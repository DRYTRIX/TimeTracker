"""
Gamification models for badges and leaderboards
"""

from datetime import datetime
from app import db
from sqlalchemy import Index


class Badge(db.Model):
    """Badge definition/configuration"""

    __tablename__ = "badges"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), nullable=True)  # Icon class or URL
    badge_type = db.Column(db.String(50), nullable=False)  # 'achievement', 'milestone', 'streak', 'special'
    
    # Criteria (JSON) - conditions to earn badge
    criteria = db.Column(db.JSON, nullable=False)
    
    # Metadata
    points = db.Column(db.Integer, default=0, nullable=False)
    rarity = db.Column(db.String(20), default="common", nullable=False)  # 'common', 'rare', 'epic', 'legendary'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Badge {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "badge_type": self.badge_type,
            "criteria": self.criteria,
            "points": self.points,
            "rarity": self.rarity,
            "is_active": self.is_active,
        }


class UserBadge(db.Model):
    """User badge achievements"""

    __tablename__ = "user_badges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), nullable=False, index=True)
    
    # Achievement metadata
    earned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    progress = db.Column(db.Integer, default=100, nullable=False)  # Progress percentage
    achievement_metadata = db.Column(db.JSON, nullable=True)  # Additional achievement data

    # Relationships
    user = db.relationship("User", backref=db.backref("badges", lazy="dynamic"))
    badge = db.relationship("Badge", backref=db.backref("user_achievements", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
        Index("ix_user_badges_user_earned", "user_id", "earned_at"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "badge_id": self.badge_id,
            "badge": self.badge.to_dict() if self.badge else None,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
            "progress": self.progress,
            "metadata": self.achievement_metadata,  # Keep "metadata" in API for backward compatibility
        }


class Leaderboard(db.Model):
    """Leaderboard configuration"""

    __tablename__ = "leaderboards"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Leaderboard type
    leaderboard_type = db.Column(db.String(50), nullable=False)  # 'time_tracked', 'tasks_completed', 'projects_completed', 'streak', 'points'
    
    # Time period
    period = db.Column(db.String(20), default="all_time", nullable=False)  # 'daily', 'weekly', 'monthly', 'all_time'
    
    # Scope
    scope = db.Column(db.String(50), nullable=True)  # 'global', 'team', 'project_{id}'
    
    # Configuration
    config = db.Column(db.JSON, nullable=True)  # Additional configuration
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Leaderboard {self.name} ({self.leaderboard_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "leaderboard_type": self.leaderboard_type,
            "period": self.period,
            "scope": self.scope,
            "config": self.config,
            "is_active": self.is_active,
        }


class LeaderboardEntry(db.Model):
    """Leaderboard ranking entry"""

    __tablename__ = "leaderboard_entries"

    id = db.Column(db.Integer, primary_key=True)
    leaderboard_id = db.Column(db.Integer, db.ForeignKey("leaderboards.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
    # Ranking data
    rank = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Period tracking
    period_start = db.Column(db.DateTime, nullable=False, index=True)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # Metadata
    entry_metadata = db.Column(db.JSON, nullable=True)
    
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    leaderboard = db.relationship("Leaderboard", backref=db.backref("entries", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("leaderboard_entries", lazy="dynamic"))

    __table_args__ = (
        Index("ix_leaderboard_entries_leaderboard_period", "leaderboard_id", "period_start"),
        Index("ix_leaderboard_entries_user_period", "user_id", "period_start"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<LeaderboardEntry rank={self.rank} score={self.score}>"

    def to_dict(self):
        return {
            "id": self.id,
            "leaderboard_id": self.leaderboard_id,
            "user_id": self.user_id,
            "rank": self.rank,
            "score": float(self.score),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "user": {
                "id": self.user.id,
                "username": self.user.username,
                "display_name": self.user.display_name
            } if self.user else None,
        }

