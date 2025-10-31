"""
Import/Export routes for data migration and GDPR compliance
"""
from flask import Blueprint, jsonify, request, send_file, current_app, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import DataImport, DataExport, User
from app.utils.data_import import (
    import_csv_time_entries,
    import_from_toggl,
    import_from_harvest,
    restore_from_backup,
    ImportError as DataImportError
)
from app.utils.data_export import (
    export_user_data_gdpr,
    export_filtered_data,
    create_backup
)
from datetime import datetime, timedelta
import os
import json

import_export_bp = Blueprint('import_export', __name__)


# ============================================================================
# Import Routes
# ============================================================================

@import_export_bp.route('/import-export')
@login_required
def import_export_page():
    """Render the import/export page"""
    return render_template('import_export/index.html')


@import_export_bp.route('/api/import/csv', methods=['POST'])
@login_required
def import_csv():
    """
    Import time entries from CSV file
    
    Expected multipart/form-data with 'file' field
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    try:
        # Read file content
        csv_content = file.read().decode('utf-8')
        
        # Create import record
        import_record = DataImport(
            user_id=current_user.id,
            import_type='csv',
            source_file=secure_filename(file.filename)
        )
        db.session.add(import_record)
        db.session.commit()
        
        # Perform import
        summary = import_csv_time_entries(
            user_id=current_user.id,
            csv_content=csv_content,
            import_record=import_record
        )
        
        return jsonify({
            'success': True,
            'import_id': import_record.id,
            'summary': summary
        }), 200
    
    except DataImportError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"CSV import error: {str(e)}")
        return jsonify({'error': 'Import failed. Please check the file format.'}), 500


@import_export_bp.route('/api/import/toggl', methods=['POST'])
@login_required
def import_toggl():
    """
    Import time entries from Toggl Track
    
    Expected JSON body:
    {
        "api_token": "...",
        "workspace_id": "...",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    api_token = data.get('api_token')
    workspace_id = data.get('workspace_id')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    
    if not all([api_token, workspace_id, start_date_str, end_date_str]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Create import record
        import_record = DataImport(
            user_id=current_user.id,
            import_type='toggl',
            source_file=f'Toggl Workspace {workspace_id}'
        )
        db.session.add(import_record)
        db.session.commit()
        
        # Perform import
        summary = import_from_toggl(
            user_id=current_user.id,
            api_token=api_token,
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            import_record=import_record
        )
        
        return jsonify({
            'success': True,
            'import_id': import_record.id,
            'summary': summary
        }), 200
    
    except DataImportError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Toggl import error: {str(e)}")
        return jsonify({'error': 'Import failed. Please check your credentials and try again.'}), 500


@import_export_bp.route('/api/import/harvest', methods=['POST'])
@login_required
def import_harvest():
    """
    Import time entries from Harvest
    
    Expected JSON body:
    {
        "account_id": "...",
        "api_token": "...",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    account_id = data.get('account_id')
    api_token = data.get('api_token')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    
    if not all([account_id, api_token, start_date_str, end_date_str]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Create import record
        import_record = DataImport(
            user_id=current_user.id,
            import_type='harvest',
            source_file=f'Harvest Account {account_id}'
        )
        db.session.add(import_record)
        db.session.commit()
        
        # Perform import
        summary = import_from_harvest(
            user_id=current_user.id,
            account_id=account_id,
            api_token=api_token,
            start_date=start_date,
            end_date=end_date,
            import_record=import_record
        )
        
        return jsonify({
            'success': True,
            'import_id': import_record.id,
            'summary': summary
        }), 200
    
    except DataImportError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Harvest import error: {str(e)}")
        return jsonify({'error': 'Import failed. Please check your credentials and try again.'}), 500


@import_export_bp.route('/api/import/status/<int:import_id>')
@login_required
def import_status(import_id):
    """Get status of an import operation"""
    import_record = DataImport.query.get_or_404(import_id)
    
    # Check permissions
    if not current_user.is_admin and import_record.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(import_record.to_dict()), 200


@import_export_bp.route('/api/import/history')
@login_required
def import_history():
    """Get import history for current user"""
    if current_user.is_admin:
        imports = DataImport.query.order_by(DataImport.started_at.desc()).limit(50).all()
    else:
        imports = DataImport.query.filter_by(user_id=current_user.id).order_by(
            DataImport.started_at.desc()
        ).limit(50).all()
    
    return jsonify({
        'imports': [imp.to_dict() for imp in imports]
    }), 200


# ============================================================================
# Export Routes
# ============================================================================

@import_export_bp.route('/api/export/gdpr', methods=['POST'])
@login_required
def export_gdpr():
    """
    Export all user data for GDPR compliance
    
    Expected JSON body:
    {
        "format": "json" | "zip"
    }
    """
    data = request.get_json() or {}
    export_format = data.get('format', 'json')
    
    if export_format not in ['json', 'zip']:
        return jsonify({'error': 'Invalid format. Use "json" or "zip"'}), 400
    
    try:
        # Create export record
        export_record = DataExport(
            user_id=current_user.id,
            export_type='gdpr',
            export_format=export_format
        )
        db.session.add(export_record)
        db.session.commit()
        
        export_record.start_processing()
        
        # Perform export
        result = export_user_data_gdpr(
            user_id=current_user.id,
            export_format=export_format
        )
        
        export_record.complete(
            file_path=result['filepath'],
            file_size=result['file_size'],
            record_count=result['record_count']
        )
        
        return jsonify({
            'success': True,
            'export_id': export_record.id,
            'filename': result['filename'],
            'download_url': f'/api/export/download/{export_record.id}'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"GDPR export error: {str(e)}")
        if 'export_record' in locals():
            export_record.fail(str(e))
        return jsonify({'error': 'Export failed. Please try again.'}), 500


@import_export_bp.route('/api/export/filtered', methods=['POST'])
@login_required
def export_filtered():
    """
    Export filtered data
    
    Expected JSON body:
    {
        "format": "json" | "csv",
        "filters": {
            "include_time_entries": true,
            "include_projects": false,
            "include_expenses": true,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "project_id": null,
            "billable_only": false
        }
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    export_format = data.get('format', 'json')
    filters = data.get('filters', {})
    
    if export_format not in ['json', 'csv']:
        return jsonify({'error': 'Invalid format. Use "json" or "csv"'}), 400
    
    try:
        # Create export record
        export_record = DataExport(
            user_id=current_user.id,
            export_type='filtered',
            export_format=export_format,
            filters=filters
        )
        db.session.add(export_record)
        db.session.commit()
        
        export_record.start_processing()
        
        # Perform export
        result = export_filtered_data(
            user_id=current_user.id,
            filters=filters,
            export_format=export_format
        )
        
        export_record.complete(
            file_path=result['filepath'],
            file_size=result['file_size'],
            record_count=result['record_count']
        )
        
        return jsonify({
            'success': True,
            'export_id': export_record.id,
            'filename': result['filename'],
            'download_url': f'/api/export/download/{export_record.id}'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Filtered export error: {str(e)}")
        if 'export_record' in locals():
            export_record.fail(str(e))
        return jsonify({'error': 'Export failed. Please try again.'}), 500


@import_export_bp.route('/api/export/backup', methods=['POST'])
@login_required
def export_backup():
    """
    Create a full database backup (admin only)
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Create export record
        export_record = DataExport(
            user_id=current_user.id,
            export_type='backup',
            export_format='json'
        )
        db.session.add(export_record)
        db.session.commit()
        
        export_record.start_processing()
        
        # Create backup
        result = create_backup(user_id=current_user.id)
        
        export_record.complete(
            file_path=result['filepath'],
            file_size=result['file_size'],
            record_count=result['record_count']
        )
        
        return jsonify({
            'success': True,
            'export_id': export_record.id,
            'filename': result['filename'],
            'download_url': f'/api/export/download/{export_record.id}'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Backup creation error: {str(e)}")
        if 'export_record' in locals():
            export_record.fail(str(e))
        return jsonify({'error': 'Backup failed. Please try again.'}), 500


@import_export_bp.route('/api/export/download/<int:export_id>')
@login_required
def download_export(export_id):
    """Download an export file"""
    export_record = DataExport.query.get_or_404(export_id)
    
    # Check permissions
    if not current_user.is_admin and export_record.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if export is complete
    if export_record.status != 'completed':
        return jsonify({'error': 'Export is not ready yet'}), 400
    
    # Check if file exists
    if not export_record.file_path or not os.path.exists(export_record.file_path):
        return jsonify({'error': 'Export file not found'}), 404
    
    # Check if expired
    if export_record.is_expired():
        return jsonify({'error': 'Export has expired'}), 410
    
    return send_file(
        export_record.file_path,
        as_attachment=True,
        download_name=os.path.basename(export_record.file_path)
    )


@import_export_bp.route('/api/export/status/<int:export_id>')
@login_required
def export_status(export_id):
    """Get status of an export operation"""
    export_record = DataExport.query.get_or_404(export_id)
    
    # Check permissions
    if not current_user.is_admin and export_record.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(export_record.to_dict()), 200


@import_export_bp.route('/api/export/history')
@login_required
def export_history():
    """Get export history for current user"""
    if current_user.is_admin:
        exports = DataExport.query.order_by(DataExport.created_at.desc()).limit(50).all()
    else:
        exports = DataExport.query.filter_by(user_id=current_user.id).order_by(
            DataExport.created_at.desc()
        ).limit(50).all()
    
    return jsonify({
        'exports': [exp.to_dict() for exp in exports]
    }), 200


# ============================================================================
# Backup/Restore Routes
# ============================================================================

@import_export_bp.route('/api/backup/restore', methods=['POST'])
@login_required
def restore_backup():
    """
    Restore from backup file (admin only)
    
    Expected multipart/form-data with 'file' field
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'File must be a JSON backup file'}), 400
    
    try:
        # Save uploaded file temporarily
        backup_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', '/data/uploads'), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(backup_dir, f'restore_{filename}')
        file.save(filepath)
        
        # Create import record
        import_record = DataImport(
            user_id=current_user.id,
            import_type='backup',
            source_file=filename
        )
        db.session.add(import_record)
        db.session.commit()
        
        # Perform restore
        statistics = restore_from_backup(
            user_id=current_user.id,
            backup_file_path=filepath
        )
        
        # Clean up temporary file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'import_id': import_record.id,
            'statistics': statistics,
            'message': 'Backup restored successfully'
        }), 200
    
    except DataImportError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Backup restore error: {str(e)}")
        return jsonify({'error': 'Restore failed. Please check the backup file.'}), 500


# ============================================================================
# Migration Wizard Routes
# ============================================================================

@import_export_bp.route('/api/migration/wizard/start', methods=['POST'])
@login_required
def start_migration_wizard():
    """
    Start the migration wizard
    
    Expected JSON body:
    {
        "source": "toggl" | "harvest" | "csv",
        "credentials": {...},
        "options": {...}
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    source = data.get('source')
    
    if source not in ['toggl', 'harvest', 'csv']:
        return jsonify({'error': 'Invalid source'}), 400
    
    # Store wizard state in session or return wizard ID
    wizard_id = f"wizard_{current_user.id}_{datetime.utcnow().timestamp()}"
    
    return jsonify({
        'success': True,
        'wizard_id': wizard_id,
        'next_step': 'credentials',
        'message': f'Migration wizard started for {source}'
    }), 200


@import_export_bp.route('/api/migration/wizard/<wizard_id>/preview', methods=['POST'])
@login_required
def preview_migration(wizard_id):
    """
    Preview data before importing
    
    This would fetch a small sample of data to show the user what will be imported
    """
    data = request.get_json()
    
    # Implementation would depend on the source
    # For now, return a mock preview
    
    return jsonify({
        'success': True,
        'preview': {
            'sample_entries': [],
            'total_count': 0,
            'date_range': {}
        }
    }), 200


@import_export_bp.route('/api/migration/wizard/<wizard_id>/execute', methods=['POST'])
@login_required
def execute_migration(wizard_id):
    """
    Execute the migration after preview
    """
    data = request.get_json()
    
    # This would trigger the actual import based on the wizard configuration
    
    return jsonify({
        'success': True,
        'message': 'Migration started',
        'import_id': None
    }), 200


# ============================================================================
# Template Endpoints
# ============================================================================

@import_export_bp.route('/api/import/template/csv')
@login_required
def download_csv_template():
    """Download CSV import template"""
    template_content = """project_name,client_name,task_name,start_time,end_time,duration_hours,notes,tags,billable
Example Project,Example Client,Example Task,2024-01-01 09:00:00,2024-01-01 10:30:00,1.5,Meeting with client,meeting;client,true
Another Project,Another Client,,2024-01-01 14:00:00,2024-01-01 16:00:00,2.0,Development work,dev;coding,true
"""
    
    from io import BytesIO
    
    buffer = BytesIO()
    buffer.write(template_content.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name='timetracker_import_template.csv'
    )

