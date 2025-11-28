from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, List, Optional, Set

from app import db
from app.models import Client, TimeEntry, ClientPrepaidConsumption, Invoice

SECONDS_IN_HOUR = Decimal("3600")
TWO_DECIMALS = Decimal("0.01")


@dataclass
class ProcessedTimeEntry:
    """Result container describing how a time entry was treated."""

    entry: TimeEntry
    billable_hours: Decimal
    prepaid_hours: Decimal
    allocation_month: Optional[date]


@dataclass
class PrepaidMonthSummary:
    """Summary of prepaid plan usage for a given cycle."""

    allocation_month: date
    plan_hours: Decimal
    consumed_hours: Decimal
    remaining_hours: Decimal


class PrepaidHoursAllocator:
    """Encapsulates prepaid hour allocation logic for a client."""

    def __init__(self, client: Client, invoice: Optional[Invoice] = None):
        self.client = client
        self.invoice = invoice
        self.plan_hours = client.prepaid_hours_decimal if client else Decimal("0")
        self.total_prepaid_hours_assigned = Decimal("0")
        self._consumed_by_period: dict[date, Decimal] = {}

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def process(self, entries: Iterable[TimeEntry]) -> List[ProcessedTimeEntry]:
        """Allocate prepaid hours for the provided time entries."""
        entries = list(entries or [])

        if not entries:
            return []

        # Always work against a deterministic ordering
        entries.sort(key=lambda e: (e.start_time or datetime.min))

        if not self.client or not self.client.prepaid_plan_enabled:
            return [
                ProcessedTimeEntry(
                    entry=entry,
                    billable_hours=self._hours_from_entry(entry),
                    prepaid_hours=Decimal("0"),
                    allocation_month=self._allocation_month(entry),
                )
                for entry in entries
            ]

        self._reset_invoice_allocations()
        months = self._collect_months(entries)
        self._load_existing_consumption(months)

        processed: List[ProcessedTimeEntry] = []

        for entry in entries:
            hours = self._hours_from_entry(entry)
            allocation_month = self._allocation_month(entry)

            if hours <= 0 or allocation_month is None:
                processed.append(
                    ProcessedTimeEntry(
                        entry=entry,
                        billable_hours=Decimal("0"),
                        prepaid_hours=Decimal("0"),
                        allocation_month=allocation_month,
                    )
                )
                continue

            remaining = self._remaining_allowance(allocation_month)
            prepaid_hours = self._quantize_hours(min(hours, remaining) if remaining > 0 else Decimal("0"))
            billable_hours = self._quantize_hours(hours - prepaid_hours)

            if prepaid_hours > 0:
                self._record_consumption(entry, allocation_month, prepaid_hours)
                entry.billable = billable_hours > 0
            else:
                entry.billable = True

            processed.append(
                ProcessedTimeEntry(
                    entry=entry,
                    billable_hours=billable_hours,
                    prepaid_hours=prepaid_hours,
                    allocation_month=allocation_month,
                )
            )

        self.total_prepaid_hours_assigned = sum((item.prepaid_hours for item in processed), Decimal("0"))
        return processed

    def build_summary(self, entries: Iterable[TimeEntry]) -> List[PrepaidMonthSummary]:
        """Return prepaid period summaries for UI purposes (no DB mutations)."""
        if not self.client or not self.client.prepaid_plan_enabled:
            return []

        entries = list(entries or [])
        months = self._collect_months(entries)
        if not months:
            return []

        # Reset local cache and load existing consumption without mutating data
        self._consumed_by_period = {}
        self._load_existing_consumption(months)

        summaries: List[PrepaidMonthSummary] = []
        for month in sorted(months):
            consumed = self._quantize_hours(self._consumed_by_period.get(month, Decimal("0")))
            remaining = self._quantize_hours(self.plan_hours - consumed)
            if remaining < 0:
                remaining = Decimal("0").quantize(TWO_DECIMALS)
            summaries.append(
                PrepaidMonthSummary(
                    allocation_month=month,
                    plan_hours=self._quantize_hours(self.plan_hours),
                    consumed_hours=consumed,
                    remaining_hours=remaining,
                )
            )
        return summaries

    # ----------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------
    def _reset_invoice_allocations(self):
        """Remove existing ledger rows tied to the invoice before recalculating."""
        if not self.invoice:
            return

        existing_allocations = ClientPrepaidConsumption.query.filter_by(invoice_id=self.invoice.id).all()
        if not existing_allocations:
            return

        entry_ids = [allocation.time_entry_id for allocation in existing_allocations]
        if entry_ids:
            entries = TimeEntry.query.filter(TimeEntry.id.in_(entry_ids)).all()
            for entry in entries:
                entry.billable = True

        ClientPrepaidConsumption.query.filter_by(invoice_id=self.invoice.id).delete(synchronize_session=False)
        db.session.flush()

    def _collect_months(self, entries: Iterable[TimeEntry]) -> Set[date]:
        months: Set[date] = set()
        for entry in entries:
            allocation_month = self._allocation_month(entry)
            if allocation_month:
                months.add(allocation_month)
        return months

    def _load_existing_consumption(self, months: Set[date]):
        if not months:
            return

        query = ClientPrepaidConsumption.query.filter(
            ClientPrepaidConsumption.client_id == self.client.id, ClientPrepaidConsumption.allocation_month.in_(months)
        )

        if self.invoice:
            query = query.filter(ClientPrepaidConsumption.invoice_id != self.invoice.id)

        for row in query:
            hours = Decimal(row.seconds_consumed or 0) / SECONDS_IN_HOUR
            month = row.allocation_month
            self._consumed_by_period[month] = self._consumed_by_period.get(month, Decimal("0")) + hours

    def _allocation_month(self, entry: TimeEntry) -> Optional[date]:
        if not entry or not entry.start_time:
            return None
        return self.client.prepaid_month_start(entry.start_time)

    def _remaining_allowance(self, month: date) -> Decimal:
        consumed = self._consumed_by_period.get(month, Decimal("0"))
        remaining = self.plan_hours - consumed
        return remaining if remaining > 0 else Decimal("0")

    def _record_consumption(self, entry: TimeEntry, month: date, prepaid_hours: Decimal):
        if prepaid_hours <= 0:
            return

        seconds = int((prepaid_hours * SECONDS_IN_HOUR).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        consumption = ClientPrepaidConsumption(
            client_id=self.client.id,
            time_entry_id=entry.id,
            invoice_id=self.invoice.id if self.invoice else None,
            allocation_month=month,
            seconds_consumed=seconds,
        )
        db.session.add(consumption)

        # Update cache to reflect newly allocated hours
        self._consumed_by_period[month] = self._consumed_by_period.get(month, Decimal("0")) + prepaid_hours

    @staticmethod
    def _hours_from_entry(entry: TimeEntry) -> Decimal:
        duration_seconds = entry.duration_seconds or 0
        return (Decimal(duration_seconds) / SECONDS_IN_HOUR).quantize(TWO_DECIMALS)

    @staticmethod
    def _quantize_hours(value: Decimal) -> Decimal:
        if value is None:
            return Decimal("0").quantize(TWO_DECIMALS)
        return value.quantize(TWO_DECIMALS)
