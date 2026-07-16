"""Unified metrics layer for analytics and forecasting."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func

from app import db
from app.models import Expense, Invoice, Payment, Project, ProjectCost, TimeEntry


class MetricsService:
    """Cross-entity metrics with shared dimensions (date, user, project, client)."""

    def profitability_by_project(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None,
        is_admin: bool = True,
    ) -> List[Dict[str, Any]]:
        """Revenue minus labor and direct costs per project."""
        entry_q = db.session.query(
            TimeEntry.project_id.label("project_id"),
            func.sum(TimeEntry.duration_seconds).label("seconds"),
        ).filter(
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_date,
            TimeEntry.start_time <= end_date,
        )
        if not is_admin and user_id:
            entry_q = entry_q.filter(TimeEntry.user_id == user_id)
        entry_q = entry_q.group_by(TimeEntry.project_id)

        labor_by_project: Dict[int, Decimal] = {}
        projects = {p.id: p for p in Project.query.all()}
        for row in entry_q.all():
            if not row.project_id:
                continue
            project = projects.get(row.project_id)
            rate = Decimal(str(project.hourly_rate or 0)) if project else Decimal("0")
            hours = Decimal(str((row.seconds or 0) / 3600))
            labor_by_project[row.project_id] = labor_by_project.get(row.project_id, Decimal("0")) + hours * rate

        expense_q = (
            db.session.query(Expense.project_id, func.sum(Expense.amount).label("total"))
            .filter(Expense.expense_date >= start_date, Expense.expense_date <= end_date)
            .group_by(Expense.project_id)
        )
        expenses_by_project = {
            row.project_id: Decimal(str(row.total or 0)) for row in expense_q.all() if row.project_id
        }

        cost_q = (
            db.session.query(ProjectCost.project_id, func.sum(ProjectCost.amount).label("total"))
            .filter(ProjectCost.cost_date >= start_date, ProjectCost.cost_date <= end_date)
            .group_by(ProjectCost.project_id)
        )
        costs_by_project = {row.project_id: Decimal(str(row.total or 0)) for row in cost_q.all() if row.project_id}

        payment_q = (
            db.session.query(Invoice.project_id, func.sum(Payment.amount).label("total"))
            .join(Payment, Payment.invoice_id == Invoice.id)
            .filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
            .group_by(Invoice.project_id)
        )
        revenue_by_project = {row.project_id: Decimal(str(row.total or 0)) for row in payment_q.all() if row.project_id}

        project_ids = set(labor_by_project) | set(expenses_by_project) | set(costs_by_project) | set(revenue_by_project)
        rows: List[Dict[str, Any]] = []
        for pid in project_ids:
            project = projects.get(pid)
            revenue = revenue_by_project.get(pid, Decimal("0"))
            labor = labor_by_project.get(pid, Decimal("0"))
            expenses = expenses_by_project.get(pid, Decimal("0"))
            costs = costs_by_project.get(pid, Decimal("0"))
            total_cost = labor + expenses + costs
            margin = revenue - total_cost
            rows.append(
                {
                    "project_id": pid,
                    "project_name": project.name if project else f"Project {pid}",
                    "revenue": float(revenue),
                    "labor_cost": float(labor),
                    "expenses": float(expenses),
                    "project_costs": float(costs),
                    "total_cost": float(total_cost),
                    "margin": float(margin),
                    "margin_percent": float((margin / revenue * 100) if revenue else 0),
                }
            )
        rows.sort(key=lambda r: r["margin"], reverse=True)
        return rows

    @staticmethod
    def linear_forecast_with_bands(
        values: List[float], forecast_days: int = 7
    ) -> Tuple[List[float], List[float], List[float]]:
        """Simple linear regression forecast with approximate 80% confidence bands."""
        n = len(values)
        if n < 2:
            avg = values[0] if values else 0.0
            return (
                [avg] * forecast_days,
                [avg * 0.85] * forecast_days,
                [avg * 1.15] * forecast_days,
            )

        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(values) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
        den = sum((x - mean_x) ** 2 for x in xs) or 1.0
        slope = num / den
        intercept = mean_y - slope * mean_x

        residuals = [values[i] - (intercept + slope * xs[i]) for i in range(n)]
        std_err = (sum(r * r for r in residuals) / max(n - 2, 1)) ** 0.5

        forecast, lower, upper = [], [], []
        for i in range(1, forecast_days + 1):
            x = n - 1 + i
            pred = intercept + slope * x
            band = 1.28 * std_err * (1 + i / n) ** 0.5
            forecast.append(round(max(0.0, pred), 2))
            lower.append(round(max(0.0, pred - band), 2))
            upper.append(round(max(0.0, pred + band), 2))
        return forecast, lower, upper

    def org_utilization_forecast(self, start_date: date, end_date: date, forecast_weeks: int = 4) -> Dict[str, Any]:
        """Admin org-level utilization projection from historical billable ratio."""
        total_seconds = (
            db.session.query(func.sum(TimeEntry.duration_seconds))
            .filter(
                TimeEntry.end_time.isnot(None), TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date
            )
            .scalar()
            or 0
        )
        billable_seconds = (
            db.session.query(func.sum(TimeEntry.duration_seconds))
            .filter(
                TimeEntry.end_time.isnot(None),
                TimeEntry.billable.is_(True),
                TimeEntry.start_time >= start_date,
                TimeEntry.start_time <= end_date,
            )
            .scalar()
            or 0
        )
        total_hours = total_seconds / 3600
        billable_hours = billable_seconds / 3600
        ratio = billable_hours / total_hours if total_hours else 0
        weeks = max((end_date - start_date).days / 7, 1)
        weekly_hours = total_hours / weeks
        projected = [round(weekly_hours * ratio, 2) for _ in range(forecast_weeks)]
        return {
            "historical_billable_ratio": round(ratio, 3),
            "avg_weekly_hours": round(weekly_hours, 2),
            "projected_billable_hours_per_week": projected,
        }
