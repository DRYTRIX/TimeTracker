"""
Initial setup routes for TimeTracker

Handles first-time setup and telemetry opt-in.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.utils.installation import get_installation_config
from app import log_event, track_event

setup_bp = Blueprint('setup', __name__)


@setup_bp.route('/setup', methods=['GET', 'POST'])
def initial_setup():
    """Initial setup page for first-time users"""
    installation_config = get_installation_config()
    
    # If setup is already complete, redirect to dashboard
    if installation_config.is_setup_complete():
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Get telemetry preference
        telemetry_enabled = request.form.get('telemetry_enabled') == 'on'
        
        # Save preference
        installation_config.mark_setup_complete(telemetry_enabled=telemetry_enabled)
        
        # Log the setup completion
        log_event("setup.completed", telemetry_enabled=telemetry_enabled)
        
        # Show success message
        if telemetry_enabled:
            flash('Setup complete! Thank you for helping us improve TimeTracker.', 'success')
        else:
            flash('Setup complete! Telemetry is disabled.', 'success')
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('setup/initial_setup.html')

