#!/usr/bin/env python3
"""
Time Tracker Application Entry Point
"""

import os
from app import create_app, db
from app.models import User, Project, TimeEntry, Task, Settings, Invoice, InvoiceItem, Client

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Add database models to Flask shell context"""
    return {
        'db': db,
        'User': User,
        'Project': Project,
        'TimeEntry': TimeEntry,
        'Task': Task,
        'Settings': Settings,
        'Invoice': Invoice,
        'InvoiceItem': InvoiceItem,
        'Client': Client
    }

@app.cli.command()
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
        print("Database initialized with default settings")
    
    # Create admin user if it doesn't exist (first username, stripped)
    admin_username = os.getenv('ADMIN_USERNAMES', 'admin').split(',')[0].strip()
    if not User.query.filter_by(username=admin_username).first():
        admin_user = User(username=admin_username, role='admin')
        db.session.add(admin_user)
        db.session.commit()
        print(f"Created admin user: {admin_username}")
    
    print("Database initialization complete!")

@app.cli.command()
def create_admin():
    """Create an admin user"""
    username = input("Enter admin username: ").strip()
    if not username:
        print("Username cannot be empty")
        return
    
    if User.query.filter_by(username=username).first():
        print(f"User {username} already exists")
        return
    
    user = User(username=username, role='admin')
    db.session.add(user)
    db.session.commit()
    print(f"Created admin user: {username}")

# Initialize kanban columns on startup if they don't exist
# This is handled by the migration system, so we skip it here

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
