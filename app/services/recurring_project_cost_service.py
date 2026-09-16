"""Service for recurring project cost business logic."""

import logging
from datetime import datetime
from typing import List, Optional

from app import db
from app.models import ProjectCost, RecurringProjectCost

logger = logging.getLogger(__name__)


class RecurringProjectCostService:
    """Service for recurring project cost operations."""

    def generate_cost(self, recurring_cost: RecurringProjectCost) -> Optional[ProjectCost]:
        if not recurring_cost.should_generate_today():
            return None

        cost_date = datetime.utcnow().date()
        cost = ProjectCost(
            project_id=recurring_cost.project_id,
            user_id=recurring_cost.user_id,
            description=recurring_cost.description,
            category=recurring_cost.category,
            amount=recurring_cost.amount,
            cost_date=cost_date,
            billable=recurring_cost.billable,
            currency_code=recurring_cost.currency_code,
            notes=f"Generated from recurring cost #{recurring_cost.id}",
        )
        db.session.add(cost)

        recurring_cost.last_generated_at = datetime.utcnow()
        recurring_cost.next_run_date = recurring_cost.calculate_next_run_date(cost_date)
        return cost

    def generate_due_recurring_costs(self) -> int:
        """Generate project costs for all due recurring templates."""
        today = datetime.utcnow().date()
        recurring_costs = RecurringProjectCost.query.filter(
            RecurringProjectCost.is_active == True,
            RecurringProjectCost.next_run_date <= today,
        ).all()

        generated = 0
        for recurring in recurring_costs:
            try:
                if recurring.end_date and today > recurring.end_date:
                    recurring.is_active = False
                    db.session.commit()
                    continue

                cost = self.generate_cost(recurring)
                if cost:
                    db.session.commit()
                    generated += 1
                    logger.info(
                        "Generated project cost %s from recurring template %s",
                        cost.id,
                        recurring.id,
                    )
            except Exception as exc:
                logger.error("Error processing recurring project cost %s: %s", recurring.id, exc)
                db.session.rollback()

        return generated

    def list_for_project(self, project_id: int, is_active: Optional[bool] = None) -> List[RecurringProjectCost]:
        query = RecurringProjectCost.query.filter_by(project_id=project_id)
        if is_active is not None:
            query = query.filter(RecurringProjectCost.is_active == is_active)
        return query.order_by(RecurringProjectCost.next_run_date.asc()).all()
