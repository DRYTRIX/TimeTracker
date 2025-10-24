import os
import click
from flask.cli import with_appcontext
from app import db
from app.models import User, Project, TimeEntry, Settings, Client, RecurringBlock
from datetime import datetime, timedelta
import shutil
from app.utils.backup import create_backup, restore_backup
from app.utils.permissions_seed import seed_all, seed_permissions, seed_roles, migrate_legacy_users

def register_cli_commands(app):
    """Register CLI commands for the application"""
    
    @app.cli.command()
    @with_appcontext
    def init_db():
        """Initialize the database with tables and default data"""
        from app.models import Settings, User
        
        # Create all tables
        db.create_all()
        
        # Initialize settings if they don't exist
        if not Settings.query.first():
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
            click.echo("Database initialized with default settings")
        
        # Ensure admin user exists and has role 'admin'
        admin_username = os.getenv('ADMIN_USERNAMES', 'admin').split(',')[0].strip().lower()
        existing = User.query.filter_by(username=admin_username).first()
        if not existing:
            admin_user = User(username=admin_username, role='admin')
            admin_user.is_active = True
            db.session.add(admin_user)
            db.session.commit()
            click.echo(f"Created admin user: {admin_username}")
        elif existing.role != 'admin':
            existing.role = 'admin'
            existing.is_active = True
            db.session.commit()
            click.echo(f"Promoted user '{admin_username}' to admin")
        
        click.echo("Database initialization complete!")

    @app.cli.command()
    @with_appcontext
    def create_admin():
        """Create an admin user"""
        username = click.prompt("Enter admin username")
        if not username:
            click.echo("Username cannot be empty")
            return
        
        if User.query.filter_by(username=username).first():
            click.echo(f"User {username} already exists")
            return
        
        user = User(username=username, role='admin')
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created admin user: {username}")

    @app.cli.command()
    @with_appcontext
    def backup_db():
        """Create a backup of the database"""
        from app.config import Config
        
        url = Config.SQLALCHEMY_DATABASE_URI
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if url.startswith('sqlite:///'):
            # SQLite file copy
            db_path = url.replace('sqlite:///', '')
            if not os.path.exists(db_path):
                click.echo(f"Database file not found: {db_path}")
                return
            backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            backup_filename = f"timetracker_backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_filename)
            shutil.copy2(db_path, backup_path)
            click.echo(f"Database backed up to: {backup_path}")
        else:
            click.echo("For PostgreSQL, please use pg_dump, e.g.: pg_dump --format=custom --dbname=\"$DATABASE_URL\" --file=backup.dump")
        
        # Clean up old backups
        if url.startswith('sqlite:///'):
            try:
                backup_retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', 30))
                cutoff_date = datetime.now() - timedelta(days=backup_retention_days)
                
                for backup_file in os.listdir(backup_dir):
                    backup_file_path = os.path.join(backup_dir, backup_file)
                    if os.path.isfile(backup_file_path):
                        file_time = datetime.fromtimestamp(os.path.getctime(backup_file_path))
                        if file_time < cutoff_date:
                            os.remove(backup_file_path)
                            click.echo(f"Removed old backup: {backup_file}")
            except Exception as e:
                click.echo(f"Warning: Could not clean up old backups: {e}")

    @app.cli.command()
    @with_appcontext
    def backup_create():
        """Create a full backup archive (DB, settings, uploads)."""
        try:
            archive_path = create_backup(click.get_current_context().obj or app)
            if archive_path:
                click.echo(f"Backup created: {archive_path}")
            else:
                click.echo("Backup failed: no archive path returned")
        except Exception as e:
            click.echo(f"Backup failed: {e}")

    @app.cli.command()
    @with_appcontext
    @click.argument('archive_path')
    def backup_restore(archive_path):
        """Restore from a backup archive and run migrations."""
        if not archive_path:
            click.echo('Usage: flask backup_restore <path_to_backup_zip>')
            return
        try:
            success, message = restore_backup(click.get_current_context().obj or app, archive_path)
            click.echo(message)
            if not success:
                raise SystemExit(1)
        except Exception as e:
            click.echo(f"Restore failed: {e}")
            raise SystemExit(1)

    @app.cli.command()
    @with_appcontext
    def migrate_to_flask_migrate():
        """Migrate from custom migration system to Flask-Migrate"""
        click.echo("This command is deprecated. Use the migration management script instead:")
        click.echo("python migrations/manage_migrations.py")
        click.echo("\nOr use Flask-Migrate commands directly:")
        click.echo("flask db init          # Initialize migrations (first time only)")
        click.echo("flask db migrate       # Create a new migration")
        click.echo("flask db upgrade       # Apply pending migrations")
        click.echo("flask db downgrade     # Rollback last migration")
        click.echo("flask db current       # Show current migration")
        click.echo("flask db history       # Show migration history")

    @app.cli.command()
    @with_appcontext
    def db_status():
        """Show database migration status"""
        try:
            from flask_migrate import current
            current()
        except Exception as e:
            click.echo(f"Error getting migration status: {e}")
            click.echo("Make sure Flask-Migrate is properly initialized")

    @app.cli.command()
    @with_appcontext
    def db_history():
        """Show database migration history"""
        try:
            from flask_migrate import history
            history()
        except Exception as e:
            click.echo(f"Error getting migration history: {e}")
            click.echo("Make sure Flask-Migrate is properly initialized")

    @app.cli.command()
    @with_appcontext
    @click.option('--days', default=7, help='Generate entries for the next N days')
    def generate_recurring(days):
        """Expand active recurring time blocks into concrete time entries for the next N days."""
        from datetime import date, time
        from app.utils.timezone import get_timezone_obj
        tz = get_timezone_obj()

        today = datetime.now(tz).date()
        end = today + timedelta(days=int(days))
        weekday_map = { 'mon':0, 'tue':1, 'wed':2, 'thu':3, 'fri':4, 'sat':5, 'sun':6 }

        blocks = RecurringBlock.query.filter_by(is_active=True).all()
        created = 0
        for b in blocks:
            start_date = b.starts_on or today
            stop_date = b.ends_on or end
            window_start = max(today, start_date)
            window_end = min(end, stop_date)
            if window_end < window_start:
                continue
            weekdays = [(w.strip().lower()) for w in (b.weekdays or '').split(',') if w.strip()]
            weekday_nums = { weekday_map[w] for w in weekdays if w in weekday_map }
            cur = window_start
            while cur <= window_end:
                if not weekday_nums or cur.weekday() in weekday_nums:
                    try:
                        sh, sm = [int(x) for x in b.start_time_local.split(':')]
                        eh, em = [int(x) for x in b.end_time_local.split(':')]
                    except Exception:
                        cur += timedelta(days=1)
                        continue
                    # Build naive datetimes in local tz then drop tzinfo for storage convention
                    start_dt = datetime(cur.year, cur.month, cur.day, sh, sm)
                    end_dt = datetime(cur.year, cur.month, cur.day, eh, em)
                    if end_dt <= start_dt:
                        cur += timedelta(days=1)
                        continue
                    # Avoid duplicates: skip if overlapping entry exists for same user/project in this window
                    exists = (
                        TimeEntry.query
                        .filter(TimeEntry.user_id == b.user_id, TimeEntry.project_id == b.project_id)
                        .filter(TimeEntry.start_time == start_dt, TimeEntry.end_time == end_dt)
                        .first()
                    )
                    if exists:
                        cur += timedelta(days=1)
                        continue
                    te = TimeEntry(
                        user_id=b.user_id,
                        project_id=b.project_id,
                        task_id=b.task_id,
                        start_time=start_dt,
                        end_time=end_dt,
                        notes=b.notes,
                        tags=b.tags,
                        source='manual',
                        billable=b.billable,
                    )
                    db.session.add(te)
                    created += 1
                cur += timedelta(days=1)
        db.session.commit()
        click.echo(f"Recurring generation complete. Created {created} entries.")

    @app.cli.command()
    @with_appcontext
    def seed_permissions_cmd():
        """Seed default permissions, roles, and migrate existing users
        
        Note: This is now optional! The database migration (flask db upgrade)
        automatically seeds permissions and roles. This command is only needed
        if you want to re-seed or update permissions after the initial migration.
        """
        if seed_all():
            click.echo("✓ Permission system initialized successfully")
        else:
            click.echo("✗ Failed to initialize permission system")
            raise SystemExit(1)

    @app.cli.command()
    @with_appcontext
    def update_permissions():
        """Update permissions and roles after system updates
        
        Use this command to add new permissions or update role definitions
        without affecting existing user role assignments.
        """
        if seed_permissions() and seed_roles():
            click.echo("✓ Permissions and roles updated successfully")
        else:
            click.echo("✗ Failed to update permissions and roles")
            raise SystemExit(1)
