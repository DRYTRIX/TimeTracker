"""Model to track donation banner interactions and user engagement metrics"""

from datetime import datetime, timedelta
from app import db


class DonationInteraction(db.Model):
    """Track user interactions with donation prompts"""

    __tablename__ = "donation_interactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
    # Interaction type
    interaction_type = db.Column(
        db.String(50), nullable=False
    )  # 'banner_dismissed', 'banner_clicked', 'link_clicked', 'page_viewed'
    
    # Context
    source = db.Column(db.String(100), nullable=True)  # 'dashboard', 'banner', 'menu', 'footer', etc.
    
    # User metrics at time of interaction (for smart prompts)
    time_entries_count = db.Column(db.Integer, nullable=True)  # Total time entries
    days_since_signup = db.Column(db.Integer, nullable=True)  # Days since user created account
    total_hours = db.Column(db.Float, nullable=True)  # Total hours tracked
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship("User", backref="donation_interactions")

    def __repr__(self):
        return f"<DonationInteraction {self.interaction_type} by user {self.user_id}>"

    @staticmethod
    def record_interaction(user_id: int, interaction_type: str, source: str = None, user_metrics: dict = None):
        """Record a donation interaction"""
        interaction = DonationInteraction(
            user_id=user_id,
            interaction_type=interaction_type,
            source=source,
        )
        
        if user_metrics:
            interaction.time_entries_count = user_metrics.get("time_entries_count")
            interaction.days_since_signup = user_metrics.get("days_since_signup")
            interaction.total_hours = user_metrics.get("total_hours")
        
        db.session.add(interaction)
        db.session.commit()
        return interaction

    @staticmethod
    def has_recent_donation_click(user_id: int, days: int = 30) -> bool:
        """Check if user clicked donation link in last N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            DonationInteraction.query.filter_by(
                user_id=user_id, interaction_type="banner_clicked"
            )
            .filter(DonationInteraction.created_at >= cutoff)
            .first()
            is not None
        ) or (
            DonationInteraction.query.filter_by(
                user_id=user_id, interaction_type="link_clicked"
            )
            .filter(DonationInteraction.created_at >= cutoff)
            .first()
            is not None
        )

    @staticmethod
    def get_user_engagement_metrics(user_id: int) -> dict:
        """Get user engagement metrics for smart prompts"""
        from app.models import TimeEntry, User
        
        user = User.query.get(user_id)
        if not user:
            return {}
        
        # Days since signup
        days_since_signup = (datetime.utcnow() - user.created_at).days if user.created_at else 0
        
        # Time entries count
        time_entries_count = TimeEntry.query.filter_by(user_id=user_id).count()
        
        # Total hours
        total_hours = user.total_hours if hasattr(user, "total_hours") else 0.0
        
        return {
            "days_since_signup": days_since_signup,
            "time_entries_count": time_entries_count,
            "total_hours": total_hours,
        }

