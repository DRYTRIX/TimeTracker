"""Parse bank statements and suggest / confirm matches against open invoices."""

from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from app import db
from app.models import Invoice
from app.models.bank_transaction import BankTransaction
from app.services.payment_service import PaymentService
from app.utils.db import safe_commit

DEFAULT_AMOUNT_TOLERANCE = Decimal("0.05")

# ISO 20022 CAMT local-name matching (namespaces stripped)
_CAMT_DATE_TAGS = ("BookgDt", "ValDt")
_CAMT_REF_TAGS = ("EndToEndId", "AcctSvcrRef", "TxId", "MndtId", "Ref")
_CAMT_NAME_TAGS = ("Nm",)


class BankReconciliationService:
    """Import CAMT.053 / CSV bank lines and reconcile to invoices."""

    def parse_csv(
        self,
        content: str,
        *,
        account_label: Optional[str] = None,
        delimiter: str = ",",
    ) -> List[Dict[str, Any]]:
        """Parse CSV with date, amount, reference, counterparty columns (flexible headers)."""
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        if not reader.fieldnames:
            return []

        field_map = self._map_csv_headers(reader.fieldnames)
        rows: List[Dict[str, Any]] = []
        for raw in reader:
            booking = self._parse_date(raw.get(field_map.get("date") or "") if field_map.get("date") else None)
            amount = self._parse_amount(raw.get(field_map.get("amount") or "") if field_map.get("amount") else None)
            if booking is None or amount is None:
                continue
            reference = (raw.get(field_map["reference"]) or "").strip() if field_map.get("reference") else ""
            counterparty = (raw.get(field_map["counterparty"]) or "").strip() if field_map.get("counterparty") else ""
            currency = (raw.get(field_map["currency"]) or "EUR").strip().upper() if field_map.get("currency") else "EUR"
            if len(currency) != 3:
                currency = "EUR"
            rows.append(
                {
                    "account_label": account_label,
                    "booking_date": booking,
                    "amount": amount,
                    "currency": currency,
                    "counterparty": counterparty or None,
                    "reference": reference or None,
                    "raw_payload": dict(raw),
                }
            )
        return rows

    def parse_camt053(
        self,
        content: str,
        *,
        account_label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Basic CAMT.053 XML parser for Ntry credit/debit entries."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid CAMT.053 XML: {exc}") from exc

        rows: List[Dict[str, Any]] = []
        for ntry in root.iter():
            if self._local(ntry.tag) != "Ntry":
                continue
            amount_el = None
            cdt_dbt = "CRDT"
            booking = None
            reference_parts: List[str] = []
            counterparty = None

            for child in ntry.iter():
                local = self._local(child.tag)
                if local == "Amt" and child.text and amount_el is None:
                    amount_el = child
                elif local == "CdtDbtInd" and child.text:
                    cdt_dbt = child.text.strip().upper()
                elif local in _CAMT_DATE_TAGS:
                    for sub in child.iter():
                        if self._local(sub.tag) == "Dt" and sub.text:
                            booking = self._parse_date(sub.text.strip()) or booking
                            break
                elif local in _CAMT_REF_TAGS and child.text:
                    reference_parts.append(child.text.strip())
                elif local in _CAMT_NAME_TAGS and child.text and counterparty is None:
                    counterparty = child.text.strip()

            if amount_el is None or not amount_el.text:
                continue
            try:
                amount = Decimal(str(amount_el.text).strip().replace(",", ""))
            except (InvalidOperation, ValueError):
                continue
            currency = (amount_el.attrib.get("Ccy") or "EUR").upper()
            if cdt_dbt in ("DBIT", "DEBIT"):
                amount = -abs(amount)
            else:
                amount = abs(amount)
            if booking is None:
                booking = date.today()
            rows.append(
                {
                    "account_label": account_label,
                    "booking_date": booking,
                    "amount": amount,
                    "currency": currency,
                    "counterparty": counterparty,
                    "reference": " ".join(reference_parts)[:255] if reference_parts else None,
                    "raw_payload": {"source": "camt053", "cdt_dbt": cdt_dbt},
                }
            )
        return rows

    def import_rows(self, parsed_rows: List[Dict[str, Any]]) -> List[BankTransaction]:
        created: List[BankTransaction] = []
        for row in parsed_rows:
            txn = BankTransaction(
                account_label=row.get("account_label"),
                booking_date=row["booking_date"],
                amount=row["amount"],
                currency=row.get("currency") or "EUR",
                counterparty=row.get("counterparty"),
                reference=row.get("reference"),
                raw_payload=row.get("raw_payload"),
                match_status=BankTransaction.MATCH_PENDING,
            )
            db.session.add(txn)
            created.append(txn)
        if created and not safe_commit("bank_txn_import", {"count": len(created)}):
            raise RuntimeError("Could not save bank transactions")
        return created

    def suggest_matches(
        self,
        transaction: BankTransaction,
        *,
        amount_tolerance: Optional[Decimal] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Suggest open invoices by amount ±tolerance and reference/invoice-number substring."""
        tolerance = amount_tolerance if amount_tolerance is not None else DEFAULT_AMOUNT_TOLERANCE
        amount = abs(Decimal(transaction.amount))
        low = amount - tolerance
        high = amount + tolerance

        open_statuses = ("unpaid", "partially_paid")
        candidates = Invoice.query.filter(Invoice.payment_status.in_(open_statuses)).all()

        ref_haystack = " ".join(filter(None, [transaction.reference or "", transaction.counterparty or ""])).lower()

        scored: List[Tuple[float, Invoice]] = []
        for inv in candidates:
            outstanding = Decimal(str(inv.outstanding_amount or 0))
            if outstanding <= 0:
                continue
            # Match against outstanding or full total within tolerance
            targets = [outstanding, Decimal(str(inv.total_amount or 0))]
            amount_ok = any(low <= abs(t) <= high for t in targets)
            if not amount_ok:
                continue

            score = 1.0
            inv_num = (inv.invoice_number or "").lower()
            if inv_num and inv_num in ref_haystack:
                score += 5.0
            elif inv_num and any(tok and tok in inv_num for tok in re.split(r"\W+", ref_haystack) if len(tok) >= 4):
                score += 3.0
            # Prefer closer amount
            best_diff = min(abs(abs(t) - amount) for t in targets)
            score += max(0.0, 1.0 - float(best_diff))
            scored.append((score, inv))

        scored.sort(key=lambda x: (-x[0], x[1].id or 0))
        results = []
        for score, inv in scored[:limit]:
            results.append(
                {
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "client_name": inv.client_name,
                    "total_amount": float(inv.total_amount or 0),
                    "outstanding_amount": float(inv.outstanding_amount or 0),
                    "currency": inv.currency_code,
                    "score": round(score, 2),
                }
            )
        return results

    def confirm_match(
        self,
        transaction_id: int,
        invoice_id: int,
        *,
        received_by: int,
        amount_tolerance: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        txn = BankTransaction.query.get(transaction_id)
        if not txn:
            return {"success": False, "message": "Bank transaction not found", "error": "not_found"}
        if txn.match_status != BankTransaction.MATCH_PENDING:
            return {"success": False, "message": "Transaction is not pending", "error": "not_pending"}

        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return {"success": False, "message": "Invoice not found", "error": "invalid_invoice"}

        pay_amount = abs(Decimal(txn.amount))
        result = PaymentService().create_payment(
            invoice_id=invoice.id,
            amount=pay_amount,
            payment_date=txn.booking_date,
            received_by=received_by,
            currency=txn.currency or invoice.currency_code,
            method="bank_transfer",
            reference=txn.reference,
            notes=f"Bank reconciliation txn #{txn.id}",
            status="completed",
        )
        if not result.get("success"):
            return result

        payment = result["payment"]
        txn.match_status = BankTransaction.MATCH_MATCHED
        txn.matched_invoice_id = invoice.id
        txn.matched_payment_id = payment.id
        if not safe_commit("bank_txn_confirm", {"txn_id": txn.id, "invoice_id": invoice.id}):
            return {
                "success": False,
                "message": "Payment created but could not update transaction",
                "error": "database_error",
            }

        return {"success": True, "message": "Matched", "transaction": txn, "payment": payment}

    def ignore_transaction(self, transaction_id: int) -> Dict[str, Any]:
        txn = BankTransaction.query.get(transaction_id)
        if not txn:
            return {"success": False, "message": "Bank transaction not found", "error": "not_found"}
        if txn.match_status == BankTransaction.MATCH_MATCHED:
            return {"success": False, "message": "Cannot ignore a matched transaction", "error": "already_matched"}
        txn.match_status = BankTransaction.MATCH_IGNORED
        if not safe_commit("bank_txn_ignore", {"txn_id": txn.id}):
            return {"success": False, "message": "Could not update transaction", "error": "database_error"}
        return {"success": True, "message": "Ignored", "transaction": txn}

    def list_queue(self, status: str = BankTransaction.MATCH_PENDING) -> List[BankTransaction]:
        q = BankTransaction.query
        if status:
            q = q.filter_by(match_status=status)
        return q.order_by(BankTransaction.booking_date.desc(), BankTransaction.id.desc()).all()

    @staticmethod
    def _local(tag: str) -> str:
        if not tag:
            return ""
        if "}" in tag:
            return tag.rsplit("}", 1)[-1]
        return tag

    @staticmethod
    def _map_csv_headers(fieldnames: List[str]) -> Dict[str, str]:
        aliases = {
            "date": {"date", "booking_date", "bookingdate", "value_date", "valuedate", "bookgdt"},
            "amount": {"amount", "amt", "value", "sum"},
            "reference": {"reference", "ref", "remittance", "description", "narration", "memo"},
            "counterparty": {"counterparty", "name", "payer", "payee", "counterpart", "party"},
            "currency": {"currency", "ccy", "curr"},
        }
        normalized = {f: re.sub(r"[^a-z0-9]", "", (f or "").lower()) for f in fieldnames}
        mapping: Dict[str, str] = {}
        for key, names in aliases.items():
            for original, norm in normalized.items():
                if norm in names:
                    mapping[key] = original
                    break
        return mapping

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y%m%d"):
            try:
                return datetime.strptime(text[:10] if len(text) >= 8 else text, fmt).date()
            except ValueError:
                continue
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None

    @staticmethod
    def _parse_amount(value: Optional[str]) -> Optional[Decimal]:
        if value is None or str(value).strip() == "":
            return None
        text = str(value).strip().replace(" ", "").replace(",", ".")
        # Handle European "1.234,56" already partially normalized; strip extra dots
        if text.count(".") > 1:
            text = text.replace(".", "", text.count(".") - 1)
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None
