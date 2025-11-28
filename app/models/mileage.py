from datetime import datetime
from decimal import Decimal
from app import db
from sqlalchemy import Index


class Mileage(db.Model):
    """Mileage tracking for business travel"""

    __tablename__ = "mileage"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"), nullable=True, index=True)

    # Trip details
    trip_date = db.Column(db.Date, nullable=False, index=True)
    purpose = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Location information
    start_location = db.Column(db.String(200), nullable=False)
    end_location = db.Column(db.String(200), nullable=False)
    start_odometer = db.Column(db.Numeric(10, 2), nullable=True)  # Optional odometer readings
    end_odometer = db.Column(db.Numeric(10, 2), nullable=True)

    # Distance and calculation
    distance_km = db.Column(db.Numeric(10, 2), nullable=False)
    distance_miles = db.Column(db.Numeric(10, 2), nullable=True)  # Computed or manual
    rate_per_km = db.Column(db.Numeric(10, 4), nullable=False)  # Rate at time of entry
    rate_per_mile = db.Column(db.Numeric(10, 4), nullable=True)
    currency_code = db.Column(db.String(3), nullable=False, default="EUR")

    # Vehicle information
    vehicle_type = db.Column(db.String(50), nullable=True)  # 'car', 'motorcycle', 'van', 'truck'
    vehicle_description = db.Column(db.String(200), nullable=True)  # e.g., "BMW 3 Series"
    license_plate = db.Column(db.String(20), nullable=True)

    # Calculated amount
    calculated_amount = db.Column(db.Numeric(10, 2), nullable=False)

    # Round trip
    is_round_trip = db.Column(db.Boolean, default=False, nullable=False)

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
    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("mileage_entries", lazy="dynamic"))
    approver = db.relationship(
        "User", foreign_keys=[approved_by], backref=db.backref("approved_mileage", lazy="dynamic")
    )
    project = db.relationship("Project", backref=db.backref("mileage_entries", lazy="dynamic"))
    client = db.relationship("Client", backref=db.backref("mileage_entries", lazy="dynamic"))
    expense = db.relationship("Expense", backref=db.backref("mileage_entry", uselist=False))

    # Indexes for common queries
    __table_args__ = (
        Index("ix_mileage_user_date", "user_id", "trip_date"),
        Index("ix_mileage_status_date", "status", "trip_date"),
    )

    def __init__(self, user_id, trip_date, purpose, start_location, end_location, distance_km, rate_per_km, **kwargs):
        self.user_id = user_id
        self.trip_date = trip_date
        self.purpose = purpose.strip()
        self.start_location = start_location.strip()
        self.end_location = end_location.strip()
        self.distance_km = Decimal(str(distance_km))
        self.rate_per_km = Decimal(str(rate_per_km))

        # Calculate amount
        self.calculated_amount = self.distance_km * self.rate_per_km

        # Optional fields
        self.description = kwargs.get("description", "").strip() if kwargs.get("description") else None
        self.project_id = kwargs.get("project_id")
        self.client_id = kwargs.get("client_id")
        self.expense_id = kwargs.get("expense_id")
        self.start_odometer = Decimal(str(kwargs.get("start_odometer"))) if kwargs.get("start_odometer") else None
        self.end_odometer = Decimal(str(kwargs.get("end_odometer"))) if kwargs.get("end_odometer") else None
        self.distance_miles = (
            Decimal(str(kwargs.get("distance_miles")))
            if kwargs.get("distance_miles")
            else self.distance_km * Decimal("0.621371")
        )
        self.rate_per_mile = Decimal(str(kwargs.get("rate_per_mile"))) if kwargs.get("rate_per_mile") else None
        self.currency_code = kwargs.get("currency_code", "EUR")
        self.vehicle_type = kwargs.get("vehicle_type")
        self.vehicle_description = kwargs.get("vehicle_description")
        self.license_plate = kwargs.get("license_plate")
        self.is_round_trip = kwargs.get("is_round_trip", False)
        self.notes = kwargs.get("notes", "").strip() if kwargs.get("notes") else None
        self.status = kwargs.get("status", "pending")

    def __repr__(self):
        return f"<Mileage {self.start_location} -> {self.end_location} ({self.distance_km} km)>"

    @property
    def total_distance_km(self):
        """Get total distance including round trip if applicable"""
        multiplier = 2 if self.is_round_trip else 1
        return float(self.distance_km) * multiplier

    @property
    def total_amount(self):
        """Get total amount including round trip if applicable"""
        multiplier = 2 if self.is_round_trip else 1
        return float(self.calculated_amount) * multiplier

    def approve(self, approved_by_user_id, notes=None):
        """Approve the mileage entry"""
        self.status = "approved"
        self.approved_by = approved_by_user_id
        self.approved_at = datetime.utcnow()
        if notes:
            self.notes = (self.notes or "") + f"\n\nApproval notes: {notes}"
        self.updated_at = datetime.utcnow()

    def reject(self, rejected_by_user_id, reason):
        """Reject the mileage entry"""
        self.status = "rejected"
        self.approved_by = rejected_by_user_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()

    def mark_as_reimbursed(self):
        """Mark this mileage entry as reimbursed"""
        self.reimbursed = True
        self.reimbursed_at = datetime.utcnow()
        self.status = "reimbursed"
        self.updated_at = datetime.utcnow()

    def create_expense(self):
        """Create an expense from this mileage entry"""
        from app.models.expense import Expense

        if self.expense_id:
            return None  # Already has an expense

        expense = Expense(
            user_id=self.user_id,
            title=f"Mileage: {self.start_location} to {self.end_location}",
            category="travel",
            amount=self.total_amount,
            expense_date=self.trip_date,
            description=f"{self.purpose}\nDistance: {self.total_distance_km} km @ {float(self.rate_per_km)} {self.currency_code}/km",
            project_id=self.project_id,
            client_id=self.client_id,
            currency_code=self.currency_code,
            status=self.status,
        )

        return expense

    def to_dict(self):
        """Convert mileage entry to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "client_id": self.client_id,
            "expense_id": self.expense_id,
            "trip_date": self.trip_date.isoformat() if self.trip_date else None,
            "purpose": self.purpose,
            "description": self.description,
            "start_location": self.start_location,
            "end_location": self.end_location,
            "start_odometer": float(self.start_odometer) if self.start_odometer else None,
            "end_odometer": float(self.end_odometer) if self.end_odometer else None,
            "distance_km": float(self.distance_km),
            "distance_miles": float(self.distance_miles) if self.distance_miles else None,
            "rate_per_km": float(self.rate_per_km),
            "rate_per_mile": float(self.rate_per_mile) if self.rate_per_mile else None,
            "currency_code": self.currency_code,
            "vehicle_type": self.vehicle_type,
            "vehicle_description": self.vehicle_description,
            "license_plate": self.license_plate,
            "calculated_amount": float(self.calculated_amount),
            "is_round_trip": self.is_round_trip,
            "total_distance_km": self.total_distance_km,
            "total_amount": self.total_amount,
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
    def get_default_rates(cls):
        """Get default mileage rates for different vehicle types"""
        # These are example rates and should be configurable in settings
        return {
            "car": {"km": 0.30, "mile": 0.48, "currency": "EUR"},
            "motorcycle": {"km": 0.20, "mile": 0.32, "currency": "EUR"},
            "van": {"km": 0.35, "mile": 0.56, "currency": "EUR"},
            "truck": {"km": 0.40, "mile": 0.64, "currency": "EUR"},
        }

    @classmethod
    def get_pending_approvals(cls, user_id=None):
        """Get mileage entries pending approval"""
        query = cls.query.filter_by(status="pending")

        if user_id:
            query = query.filter(cls.user_id == user_id)

        return query.order_by(cls.trip_date.desc()).all()

    @classmethod
    def get_total_distance(cls, user_id=None, start_date=None, end_date=None):
        """Calculate total distance traveled"""
        query = db.session.query(db.func.sum(cls.distance_km))

        if user_id:
            query = query.filter(cls.user_id == user_id)

        if start_date:
            query = query.filter(cls.trip_date >= start_date)

        if end_date:
            query = query.filter(cls.trip_date <= end_date)

        query = query.filter(cls.status.in_(["approved", "reimbursed"]))

        total = query.scalar() or Decimal("0")
        return float(total)
