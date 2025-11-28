"""
Service for quote business logic.
"""

from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import func
from app import db
from app.repositories import ClientRepository
from app.models import Quote, Client
from app.utils.db import safe_commit
from app.utils.timezone import local_now


class QuoteService:
    """Service for quote operations"""

    def __init__(self):
        self.client_repo = ClientRepository()

    def list_quotes(
        self,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        status: Optional[str] = None,
        search: Optional[str] = None,
        include_analytics: bool = False,
    ) -> Dict[str, Any]:
        """
        List quotes with filtering and optional analytics.
        Uses eager loading to prevent N+1 queries.

        Returns:
            dict with 'quotes' and optionally 'analytics' keys
        """
        from sqlalchemy.orm import joinedload

        query = Quote.query.options(joinedload(Quote.client))

        # Permission filter - non-admins only see their quotes
        if not is_admin and user_id:
            query = query.filter(Quote.created_by == user_id)

        # Apply filters
        if status and status != "all":
            query = query.filter(Quote.status == status)

        if search:
            like = f"%{search}%"
            query = query.join(Client).filter(
                db.or_(
                    Quote.title.ilike(like),
                    Quote.quote_number.ilike(like),
                    Quote.description.ilike(like),
                    Client.name.ilike(like),
                )
            )

        quotes = query.order_by(Quote.created_at.desc()).all()

        # Calculate analytics if requested
        analytics = None
        if include_analytics:
            analytics = self._calculate_analytics(user_id, is_admin)

        return {"quotes": quotes, "analytics": analytics}

    def _calculate_analytics(self, user_id: Optional[int], is_admin: bool) -> Dict[str, Any]:
        """Calculate quote analytics"""
        analytics_query = Quote.query
        if not is_admin and user_id:
            analytics_query = analytics_query.filter_by(created_by=user_id)

        # Total quotes
        total_quotes = analytics_query.count()

        # Quotes by status
        quotes_by_status = {}
        for status_val in ["draft", "sent", "accepted", "rejected", "expired"]:
            count = analytics_query.filter_by(status=status_val).count()
            quotes_by_status[status_val] = count

        # Total quote value
        total_value = analytics_query.with_entities(func.sum(Quote.total_amount)).scalar() or 0

        # Accepted quotes value
        accepted_value = (
            analytics_query.filter_by(status="accepted").with_entities(func.sum(Quote.total_amount)).scalar() or 0
        )

        # Acceptance rate
        sent_count = quotes_by_status.get("sent", 0)
        accepted_count = quotes_by_status.get("accepted", 0)
        acceptance_rate = (accepted_count / sent_count * 100) if sent_count > 0 else 0

        # Average quote value
        avg_value = (total_value / total_quotes) if total_quotes > 0 else 0

        # Quotes in last 30 days
        thirty_days_ago = local_now() - timedelta(days=30)
        recent_quotes = analytics_query.filter(Quote.created_at >= thirty_days_ago).count()

        # Quotes by client (top 10)
        quotes_by_client_query = (
            db.session.query(
                Client.name, func.count(Quote.id).label("count"), func.sum(Quote.total_amount).label("total")
            )
            .join(Quote)
            .group_by(Client.id, Client.name)
        )
        if not is_admin and user_id:
            quotes_by_client_query = quotes_by_client_query.filter(Quote.created_by == user_id)
        quotes_by_client = quotes_by_client_query.order_by(func.count(Quote.id).desc()).limit(10).all()

        return {
            "total_quotes": total_quotes,
            "quotes_by_status": quotes_by_status,
            "total_value": float(total_value),
            "accepted_value": float(accepted_value),
            "acceptance_rate": round(acceptance_rate, 1),
            "avg_value": float(avg_value),
            "recent_quotes": recent_quotes,
            "quotes_by_client": [
                {"name": name, "count": count, "total": float(total)} for name, count, total in quotes_by_client
            ],
        }

    def get_quote_with_details(self, quote_id: int, user_id: Optional[int] = None, is_admin: bool = False) -> Optional[Quote]:
        """
        Get quote with all related data using eager loading.

        Args:
            quote_id: The quote ID
            user_id: User ID for permission check
            is_admin: Whether user is admin

        Returns:
            Quote with eagerly loaded relations, or None if not found
        """
        from sqlalchemy.orm import joinedload

        query = Quote.query.options(joinedload(Quote.client), joinedload(Quote.items))

        # Permission check
        if not is_admin and user_id:
            query = query.filter(Quote.created_by == user_id)

        return query.filter_by(id=quote_id).first()

    def create_quote(
        self,
        client_id: int,
        title: str,
        created_by: int,
        description: Optional[str] = None,
        total_amount: Optional[Decimal] = None,
        hourly_rate: Optional[Decimal] = None,
        estimated_hours: Optional[float] = None,
        tax_rate: Optional[Decimal] = None,
        currency_code: Optional[str] = None,
        valid_until: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Create a new quote.

        Returns:
            dict with 'success', 'message', and 'quote' keys
        """
        # Validate client
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return {"success": False, "message": "Invalid client", "error": "invalid_client"}

        # Generate quote number if not provided
        quote_number = Quote.generate_quote_number()

        # Calculate total if hourly rate and hours provided
        if hourly_rate and estimated_hours and not total_amount:
            total_amount = Decimal(str(hourly_rate)) * Decimal(str(estimated_hours))

        # Create quote
        quote = Quote(
            quote_number=quote_number,
            client_id=client_id,
            title=title,
            description=description,
            total_amount=total_amount or Decimal("0.00"),
            hourly_rate=hourly_rate,
            estimated_hours=estimated_hours,
            tax_rate=tax_rate or Decimal("0.00"),
            currency_code=currency_code or "EUR",
            valid_until=valid_until,
            status="draft",
            created_by=created_by,
        )

        db.session.add(quote)

        if not safe_commit("create_quote", {"client_id": client_id, "created_by": created_by}):
            return {
                "success": False,
                "message": "Could not create quote due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Quote created successfully", "quote": quote}

    def update_quote(self, quote_id: int, user_id: int, is_admin: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Update a quote.

        Returns:
            dict with 'success', 'message', and 'quote' keys
        """
        quote = Quote.query.get(quote_id)
        if not quote:
            return {"success": False, "message": "Quote not found", "error": "not_found"}

        # Check permissions
        if not is_admin and quote.created_by != user_id:
            return {"success": False, "message": "Access denied", "error": "access_denied"}

        # Update fields
        for field in ("title", "description", "status", "currency_code"):
            if field in kwargs:
                setattr(quote, field, kwargs[field])
        if "total_amount" in kwargs:
            quote.total_amount = kwargs["total_amount"]
        if "hourly_rate" in kwargs:
            quote.hourly_rate = kwargs["hourly_rate"]
        if "estimated_hours" in kwargs:
            quote.estimated_hours = kwargs["estimated_hours"]
        if "tax_rate" in kwargs:
            quote.tax_rate = kwargs["tax_rate"]
        if "valid_until" in kwargs:
            quote.valid_until = kwargs["valid_until"]

        if not safe_commit("update_quote", {"quote_id": quote_id, "user_id": user_id}):
            return {
                "success": False,
                "message": "Could not update quote due to a database error",
                "error": "database_error",
            }

        return {"success": True, "message": "Quote updated successfully", "quote": quote}

