"""API Token model for REST API authentication"""
import secrets
from datetime import datetime, timedelta
from app import db
from sqlalchemy.orm import relationship


class ApiToken(db.Model):
    """API Token for authenticating REST API requests"""
    
    __tablename__ = 'api_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    token_prefix = db.Column(db.String(10), nullable=False)  # First 8 chars for identification
    
    # Ownership and permissions
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = relationship('User', backref='api_tokens')
    
    # Scopes for fine-grained permissions (comma-separated)
    # Examples: read:projects, write:time_entries, admin:all
    scopes = db.Column(db.Text, default='')
    
    # Token lifecycle
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # IP restrictions (comma-separated list of allowed IPs/CIDR blocks)
    ip_whitelist = db.Column(db.Text)
    
    # Usage tracking
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    
    def __repr__(self):
        return f'<ApiToken {self.name} ({self.token_prefix}...)>'
    
    @staticmethod
    def generate_token():
        """Generate a new secure random token"""
        # Format: tt_<32 random chars>
        random_part = secrets.token_urlsafe(32)[:32]
        return f"tt_{random_part}"
    
    @staticmethod
    def hash_token(token):
        """Hash a token for storage"""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
    
    @classmethod
    def create_token(cls, user_id, name, description='', scopes='', expires_days=None):
        """Create a new API token
        
        Args:
            user_id: User ID who owns this token
            name: Human-readable name for the token
            description: Optional description
            scopes: Comma-separated list of scopes
            expires_days: Number of days until expiration (None = never expires)
        
        Returns:
            tuple: (ApiToken instance, plain_token)
        """
        plain_token = cls.generate_token()
        token_hash = cls.hash_token(plain_token)
        token_prefix = plain_token[:8]
        
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        api_token = cls(
            name=name,
            description=description,
            token_hash=token_hash,
            token_prefix=token_prefix,
            user_id=user_id,
            scopes=scopes,
            expires_at=expires_at
        )
        
        return api_token, plain_token
    
    def verify_token(self, plain_token):
        """Verify if the provided token matches this record"""
        return self.token_hash == self.hash_token(plain_token)
    
    def is_valid(self):
        """Check if token is valid (active and not expired)"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def has_scope(self, required_scope):
        """Check if token has a specific scope
        
        Args:
            required_scope: The scope to check (e.g., 'read:projects')
        
        Returns:
            bool: True if token has the scope
        """
        if not self.scopes:
            return False
        
        token_scopes = [s.strip() for s in self.scopes.split(',')]
        
        # Check for wildcard admin scope
        if 'admin:all' in token_scopes or '*' in token_scopes:
            return True
        
        # Check for exact match
        if required_scope in token_scopes:
            return True
        
        # Check for wildcard resource scope (e.g., read:* matches read:projects)
        resource_type = required_scope.split(':')[0] if ':' in required_scope else None
        if resource_type and f"{resource_type}:*" in token_scopes:
            return True
        
        return False
    
    def record_usage(self, ip_address=None):
        """Record token usage"""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1
        db.session.commit()
    
    def to_dict(self, include_token=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'token_prefix': self.token_prefix,
            'scopes': self.scopes.split(',') if self.scopes else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'user_id': self.user_id
        }
        
        return data

