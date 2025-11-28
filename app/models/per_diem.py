from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from sqlalchemy import Index


class PerDiemRate(db.Model):
    """Per diem rate configuration for different locations"""

    __tablename__ = "per_diem_rates"

    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(100), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=True, index=True)

    # Rates
    full_day_rate = db.Column(db.Numeric(10, 2), nullable=False)
    half_day_rate = db.Column(db.Numeric(10, 2), nullable=False)
    breakfast_rate = db.Column(db.Numeric(10, 2), nullable=True)
    lunch_rate = db.Column(db.Numeric(10, 2), nullable=True)
    dinner_rate = db.Column(db.Numeric(10, 2), nullable=True)
    incidental_rate = db.Column(db.Numeric(10, 2), nullable=True)  # Tips, etc.

    currency_code = db.Column(db.String(3), nullable=False, default="EUR")

    # Validity period
    effective_from = db.Column(db.Date, nullable=False, index=True)
    effective_to = db.Column(db.Date, nullable=True, index=True)

    # Settings
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_per_diem_rates_country_city", "country", "city"),
        Index("ix_per_diem_rates_effective", "effective_from", "effective_to"),
    )

    def __init__(self, country, full_day_rate, half_day_rate, effective_from, **kwargs):
        self.country = country.strip()
        self.city = kwargs.get("city", "").strip() if kwargs.get("city") else None
        self.full_day_rate = Decimal(str(full_day_rate))
        self.half_day_rate = Decimal(str(half_day_rate))
        self.breakfast_rate = Decimal(str(kwargs.get("breakfast_rate"))) if kwargs.get("breakfast_rate") else None
        self.lunch_rate = Decimal(str(kwargs.get("lunch_rate"))) if kwargs.get("lunch_rate") else None
        self.dinner_rate = Decimal(str(kwargs.get("dinner_rate"))) if kwargs.get("dinner_rate") else None
        self.incidental_rate = Decimal(str(kwargs.get("incidental_rate"))) if kwargs.get("incidental_rate") else None
        self.currency_code = kwargs.get("currency_code", "EUR")
        self.effective_from = effective_from
        self.effective_to = kwargs.get("effective_to")
        self.is_active = kwargs.get("is_active", True)
        self.notes = kwargs.get("notes", "").strip() if kwargs.get("notes") else None

    def __repr__(self):
        location = f"{self.city}, {self.country}" if self.city else self.country
        return f"<PerDiemRate {location}: {self.full_day_rate} {self.currency_code}>"

    def to_dict(self):
        """Convert rate to dictionary for API responses"""
        return {
            "id": self.id,
            "country": self.country,
            "city": self.city,
            "full_day_rate": float(self.full_day_rate),
            "half_day_rate": float(self.half_day_rate),
            "breakfast_rate": float(self.breakfast_rate) if self.breakfast_rate else None,
            "lunch_rate": float(self.lunch_rate) if self.lunch_rate else None,
            "dinner_rate": float(self.dinner_rate) if self.dinner_rate else None,
            "incidental_rate": float(self.incidental_rate) if self.incidental_rate else None,
            "currency_code": self.currency_code,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "is_active": self.is_active,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_rate_for_location(cls, country, city=None, date=None):
        """Get applicable per diem rate for a location and date"""
        from datetime import date as dt_date

        if date is None:
            date = dt_date.today()

        query = cls.query.filter(cls.country == country, cls.is_active == True, cls.effective_from <= date)

        if city:
            # Try to find city-specific rate first
            city_rate = (
                query.filter(cls.city == city)
                .filter(db.or_(cls.effective_to.is_(None), cls.effective_to >= date))
                .first()
            )

            if city_rate:
                return city_rate

        # Fall back to country rate
        country_rate = (
            query.filter(cls.city.is_(None))
            .filter(db.or_(cls.effective_to.is_(None), cls.effective_to >= date))
            .first()
        )

        return country_rate


class PerDiem(db.Model):
    """Per diem claim for business travel"""

    __tablename__ = "per_diems"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"), nullable=True, index=True)
    per_diem_rate_id = db.Column(db.Integer, db.ForeignKey("per_diem_rates.id"), nullable=True, index=True)

    # Trip details
    trip_purpose = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Date range
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    departure_time = db.Column(db.Time, nullable=True)
    return_time = db.Column(db.Time, nullable=True)

    # Location
    country = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=True)

    # Calculation details
    full_days = db.Column(db.Integer, default=0, nullable=False)
    half_days = db.Column(db.Integer, default=0, nullable=False)

    # Meal deductions (if meals were provided)
    breakfast_provided = db.Column(db.Integer, default=0, nullable=False)  # Number of breakfasts
    lunch_provided = db.Column(db.Integer, default=0, nullable=False)
    dinner_provided = db.Column(db.Integer, default=0, nullable=False)

    # Rates used (stored at time of creation)
    full_day_rate = db.Column(db.Numeric(10, 2), nullable=False)
    half_day_rate = db.Column(db.Numeric(10, 2), nullable=False)
    breakfast_deduction = db.Column(db.Numeric(10, 2), nullable=True)
    lunch_deduction = db.Column(db.Numeric(10, 2), nullable=True)
    dinner_deduction = db.Column(db.Numeric(10, 2), nullable=True)

    # Calculated amount
    calculated_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default="EUR")

    # Status and approval
    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # 'pending', 'approved', 'rejected', 'reimbursed'
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Reimbursement
    reimbursed = db.Column(db.Boolean, default=False, nullable=False)
    reimbursed_at = db.Column(db.DateTime, nullable=True)

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("per_diem_claims", lazy="dynamic"))
    approver = db.relationship(
        "User", foreign_keys=[approved_by], backref=db.backref("approved_per_diems", lazy="dynamic")
    )
    project = db.relationship("Project", backref=db.backref("per_diem_claims", lazy="dynamic"))
    client = db.relationship("Client", backref=db.backref("per_diem_claims", lazy="dynamic"))
    expense = db.relationship("Expense", backref=db.backref("per_diem_claim", uselist=False))
    rate = db.relationship("PerDiemRate", backref=db.backref("per_diem_claims", lazy="dynamic"))

    # Indexes for common queries
    __table_args__ = (
        Index("ix_per_diems_user_date", "user_id", "start_date"),
        Index("ix_per_diems_status_date", "status", "start_date"),
    )

    def __init__(self, user_id, trip_purpose, start_date, end_date, country, full_day_rate, half_day_rate, **kwargs):
        self.user_id = user_id
        self.trip_purpose = trip_purpose.strip()
        self.start_date = start_date
        self.end_date = end_date
        self.country = country.strip()
        self.city = kwargs.get("city", "").strip() if kwargs.get("city") else None

        # Store rates
        self.full_day_rate = Decimal(str(full_day_rate))
        self.half_day_rate = Decimal(str(half_day_rate))

        # Optional fields
        self.description = kwargs.get("description", "").strip() if kwargs.get("description") else None
        self.project_id = kwargs.get("project_id")
        self.client_id = kwargs.get("client_id")
        self.expense_id = kwargs.get("expense_id")
        self.per_diem_rate_id = kwargs.get("per_diem_rate_id")
        self.departure_time = kwargs.get("departure_time")
        self.return_time = kwargs.get("return_time")
        self.full_days = kwargs.get("full_days", 0)
        self.half_days = kwargs.get("half_days", 0)
        self.breakfast_provided = kwargs.get("breakfast_provided", 0)
        self.lunch_provided = kwargs.get("lunch_provided", 0)
        self.dinner_provided = kwargs.get("dinner_provided", 0)
        self.breakfast_deduction = Decimal(str(kwargs.get("breakfast_deduction", 0)))
        self.lunch_deduction = Decimal(str(kwargs.get("lunch_deduction", 0)))
        self.dinner_deduction = Decimal(str(kwargs.get("dinner_deduction", 0)))
        self.currency_code = kwargs.get("currency_code", "EUR")
        self.notes = kwargs.get("notes", "").strip() if kwargs.get("notes") else None
        self.status = kwargs.get("status", "pending")

        # Calculate amount
        self.calculated_amount = self._calculate_amount()

    def _calculate_amount(self):
        """Calculate the per diem amount based on days and deductions"""
        # Base amount
        amount = (self.full_day_rate * self.full_days) + (self.half_day_rate * self.half_days)

        # Deduct provided meals
        amount -= self.breakfast_deduction * self.breakfast_provided
        amount -= self.lunch_deduction * self.lunch_provided
        amount -= self.dinner_deduction * self.dinner_provided

        return max(Decimal("0"), amount)  # Ensure non-negative

    def recalculate_amount(self):
        """Recalculate the amount (useful when days or deductions change)"""
        self.calculated_amount = self._calculate_amount()
        return self.calculated_amount

    def __repr__(self):
        location = f"{self.city}, {self.country}" if self.city else self.country
        return f"<PerDiem {location} ({self.start_date} - {self.end_date})>"

    @property
    def total_days(self):
        """Get total number of days (full + half)"""
        return self.full_days + (self.half_days * 0.5)

    @property
    def trip_duration(self):
        """Get trip duration in days"""
        return (self.end_date - self.start_date).days + 1

    def approve(self, approved_by_user_id, notes=None):
        """Approve the per diem claim"""
        self.status = "approved"
        self.approved_by = approved_by_user_id
        self.approved_at = datetime.utcnow()
        if notes:
            self.notes = (self.notes or "") + f"\n\nApproval notes: {notes}"
        self.updated_at = datetime.utcnow()

    def reject(self, rejected_by_user_id, reason):
        """Reject the per diem claim"""
        self.status = "rejected"
        self.approved_by = rejected_by_user_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()

    def mark_as_reimbursed(self):
        """Mark this per diem claim as reimbursed"""
        self.reimbursed = True
        self.reimbursed_at = datetime.utcnow()
        self.status = "reimbursed"
        self.updated_at = datetime.utcnow()

    def create_expense(self):
        """Create an expense from this per diem claim"""
        from app.models.expense import Expense

        if self.expense_id:
            return None  # Already has an expense

        location = f"{self.city}, {self.country}" if self.city else self.country

        expense = Expense(
            user_id=self.user_id,
            title=f"Per Diem: {location}",
            category="meals",
            amount=self.calculated_amount,
            expense_date=self.start_date,
            description=f"{self.trip_purpose}\n{self.start_date} to {self.end_date} ({self.total_days} days)",
            project_id=self.project_id,
            client_id=self.client_id,
            currency_code=self.currency_code,
            status=self.status,
        )

        return expense

    def to_dict(self):
        """Convert per diem claim to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "client_id": self.client_id,
            "expense_id": self.expense_id,
            "per_diem_rate_id": self.per_diem_rate_id,
            "trip_purpose": self.trip_purpose,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "departure_time": self.departure_time.isoformat() if self.departure_time else None,
            "return_time": self.return_time.isoformat() if self.return_time else None,
            "country": self.country,
            "city": self.city,
            "full_days": self.full_days,
            "half_days": self.half_days,
            "total_days": self.total_days,
            "trip_duration": self.trip_duration,
            "breakfast_provided": self.breakfast_provided,
            "lunch_provided": self.lunch_provided,
            "dinner_provided": self.dinner_provided,
            "full_day_rate": float(self.full_day_rate),
            "half_day_rate": float(self.half_day_rate),
            "breakfast_deduction": float(self.breakfast_deduction) if self.breakfast_deduction else None,
            "lunch_deduction": float(self.lunch_deduction) if self.lunch_deduction else None,
            "dinner_deduction": float(self.dinner_deduction) if self.dinner_deduction else None,
            "calculated_amount": float(self.calculated_amount),
            "currency_code": self.currency_code,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "reimbursed": self.reimbursed,
            "reimbursed_at": self.reimbursed_at.isoformat() if self.reimbursed_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.username if self.user else None,
            "project": self.project.name if self.project else None,
            "client": self.client.name if self.client else None,
            "approver": self.approver.username if self.approver else None,
        }

    @classmethod
    def calculate_days_from_dates(cls, start_date, end_date, departure_time=None, return_time=None):
        """
        Calculate full and half days based on departure and return times.

        Rules:
        - Departure before 12:00 = full day
        - Departure after 12:00 = half day
        - Return after 12:00 = full day
        - Return before 12:00 = half day
        - Middle days = full days
        """
        from datetime import time as dt_time

        if start_date > end_date:
            return {"full_days": 0, "half_days": 0}

        trip_days = (end_date - start_date).days + 1

        if trip_days == 1:
            # Single day trip
            if departure_time and return_time:
                # Check if it qualifies for a full day (>= 8 hours)
                departure_datetime = datetime.combine(start_date, departure_time)
                return_datetime = datetime.combine(end_date, return_time)
                hours = (return_datetime - departure_datetime).total_seconds() / 3600

                if hours >= 8:
                    return {"full_days": 1, "half_days": 0}
                else:
                    return {"full_days": 0, "half_days": 1}
            else:
                # Default to half day for single day
                return {"full_days": 0, "half_days": 1}

        full_days = 0
        half_days = 0

        # First day
        noon = dt_time(12, 0)
        if departure_time and departure_time < noon:
            full_days += 1
        else:
            half_days += 1

        # Middle days (all full days)
        if trip_days > 2:
            full_days += trip_days - 2

        # Last day
        if return_time and return_time >= noon:
            full_days += 1
        else:
            half_days += 1

        return {"full_days": full_days, "half_days": half_days}

    @classmethod
    def get_pending_approvals(cls, user_id=None):
        """Get per diem claims pending approval"""
        query = cls.query.filter_by(status="pending")

        if user_id:
            query = query.filter(cls.user_id == user_id)

        return query.order_by(cls.start_date.desc()).all()
