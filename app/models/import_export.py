"""
Import/Export tracking models for data import/export operations
"""

from datetime import datetime
from app import db


class DataImport(db.Model):
    """Model to track import operations"""

    __tablename__ = "data_imports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    import_type = db.Column(db.String(50), nullable=False)  # 'csv', 'toggl', 'harvest', 'backup'
    source_file = db.Column(db.String(500), nullable=True)  # Original filename
    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # 'pending', 'processing', 'completed', 'failed', 'partial'
    total_records = db.Column(db.Integer, default=0)
    successful_records = db.Column(db.Integer, default=0)
    failed_records = db.Column(db.Integer, default=0)
    error_log = db.Column(db.Text, nullable=True)  # JSON string of errors
    import_summary = db.Column(db.Text, nullable=True)  # JSON string with details
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationship
    user = db.relationship("User", backref=db.backref("imports", lazy="dynamic"))

    def __init__(self, user_id, import_type, source_file=None):
        self.user_id = user_id
        self.import_type = import_type
        self.source_file = source_file
        self.status = "pending"
        self.total_records = 0
        self.successful_records = 0
        self.failed_records = 0

    def __repr__(self):
        return f"<DataImport {self.id}: {self.import_type} by {self.user.username}>"

    def start_processing(self):
        """Mark import as processing"""
        self.status = "processing"
        db.session.commit()

    def complete(self):
        """Mark import as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def fail(self, error_message=None):
        """Mark import as failed"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        if error_message:
            import json

            errors = []
            if self.error_log:
                try:
                    errors = json.loads(self.error_log)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    # If error_log is corrupted, start fresh
                    import logging
                    logging.getLogger(__name__).warning(f"Could not parse error_log: {e}")
                    pass
            errors.append({"error": error_message, "timestamp": datetime.utcnow().isoformat()})
            self.error_log = json.dumps(errors)
        db.session.commit()

    def partial_complete(self):
        """Mark import as partially completed (some records failed)"""
        self.status = "partial"
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def update_progress(self, total, successful, failed):
        """Update import progress"""
        self.total_records = total
        self.successful_records = successful
        self.failed_records = failed
        if failed > 0 and successful > 0:
            self.status = "partial"
        elif failed > 0:
            self.status = "failed"
        db.session.commit()

    def add_error(self, error_message, record_data=None):
        """Add an error to the error log"""
        import json

        errors = []
        if self.error_log:
            try:
                errors = json.loads(self.error_log)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                # If error_log is corrupted, start fresh
                import logging
                logging.getLogger(__name__).warning(f"Could not parse error_log: {e}")
                pass

        error_entry = {"error": error_message, "timestamp": datetime.utcnow().isoformat()}
        if record_data:
            error_entry["record"] = record_data

        errors.append(error_entry)
        self.error_log = json.dumps(errors)
        db.session.commit()

    def set_summary(self, summary_dict):
        """Set import summary"""
        import json

        self.import_summary = json.dumps(summary_dict)
        db.session.commit()

    def to_dict(self):
        """Convert to dictionary"""
        import json

        return {
            "id": self.id,
            "user_id": self.user_id,
            "user": self.user.username if self.user else None,
            "import_type": self.import_type,
            "source_file": self.source_file,
            "status": self.status,
            "total_records": self.total_records,
            "successful_records": self.successful_records,
            "failed_records": self.failed_records,
            "error_log": json.loads(self.error_log) if self.error_log else [],
            "import_summary": json.loads(self.import_summary) if self.import_summary else {},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class DataExport(db.Model):
    """Model to track export operations"""

    __tablename__ = "data_exports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    export_type = db.Column(db.String(50), nullable=False)  # 'full', 'filtered', 'backup', 'gdpr'
    export_format = db.Column(db.String(20), nullable=False)  # 'json', 'csv', 'xlsx', 'zip'
    file_path = db.Column(db.String(500), nullable=True)  # Path to generated file
    file_size = db.Column(db.Integer, nullable=True)  # File size in bytes
    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # 'pending', 'processing', 'completed', 'failed'
    filters = db.Column(db.Text, nullable=True)  # JSON string with export filters
    record_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # When file should be deleted

    # Relationship
    user = db.relationship("User", backref=db.backref("exports", lazy="dynamic"))

    def __init__(self, user_id, export_type, export_format="json", filters=None):
        self.user_id = user_id
        self.export_type = export_type
        self.export_format = export_format
        self.status = "pending"
        self.record_count = 0
        if filters:
            import json

            self.filters = json.dumps(filters)

    def __repr__(self):
        return f"<DataExport {self.id}: {self.export_type} by {self.user.username}>"

    def start_processing(self):
        """Mark export as processing"""
        self.status = "processing"
        db.session.commit()

    def complete(self, file_path, file_size, record_count):
        """Mark export as completed"""
        self.status = "completed"
        self.file_path = file_path
        self.file_size = file_size
        self.record_count = record_count
        self.completed_at = datetime.utcnow()
        # Set expiration to 7 days from now
        self.expires_at = datetime.utcnow() + timedelta(days=7)
        db.session.commit()

    def fail(self, error_message):
        """Mark export as failed"""
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def is_expired(self):
        """Check if export has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        """Convert to dictionary"""
        import json

        return {
            "id": self.id,
            "user_id": self.user_id,
            "user": self.user.username if self.user else None,
            "export_type": self.export_type,
            "export_format": self.export_format,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "status": self.status,
            "filters": json.loads(self.filters) if self.filters else {},
            "record_count": self.record_count,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
        }


# Fix missing import
from datetime import timedelta
