"""REST API v1 - Comprehensive API endpoints with token authentication"""
from flask import Blueprint, jsonify, request, current_app, g
from app import db
from app.models import (
    User,
    Project,
    TimeEntry,
    Task,
    Client,
    Invoice,
    Expense,
    SavedFilter,
    FocusSession,
    RecurringBlock,
    Comment,
    Payment,
    Mileage,
    PerDiem,
    PerDiemRate,
    BudgetAlert,
    CalendarEvent,
    KanbanColumn,
    TimeEntryTemplate,
    CreditNote,
    RecurringInvoice,
    ClientNote,
    ProjectCost,
    TaxRule,
    Currency,
    ExchangeRate,
    UserFavoriteProject,
    Activity,
    AuditLog,
    InvoicePDFTemplate,
    InvoiceTemplate,
)
from app.utils.api_auth import require_api_token
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from app.utils.timezone import parse_local_datetime, utc_to_local
from app.models.time_entry import local_now

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


# ==================== Helper Functions ====================

def paginate_query(query, page=None, per_page=None):
    """Paginate a SQLAlchemy query"""
    page = page or int(request.args.get('page', 1))
    per_page = per_page or int(request.args.get('per_page', 50))
    per_page = min(per_page, 100)  # Max 100 items per page
    
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return {
        'items': paginated.items,
        'pagination': {
            'page': paginated.page,
            'per_page': paginated.per_page,
            'total': paginated.total,
            'pages': paginated.pages,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
            'next_page': paginated.page + 1 if paginated.has_next else None,
            'prev_page': paginated.page - 1 if paginated.has_prev else None
        }
    }


def parse_datetime(dt_str):
    """Parse datetime string from API request"""
    if not dt_str:
        return None
    try:
        # Handle ISO format with timezone
        ts = dt_str.strip()
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        dt = datetime.fromisoformat(ts)
        # Convert to local naive for storage
        if dt.tzinfo is not None:
            dt = utc_to_local(dt).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _parse_date(dstr):
    """Parse a YYYY-MM-DD string to date."""
    if not dstr:
        return None
    try:
        from datetime import date as _date
        return _date.fromisoformat(str(dstr))
    except Exception:
        return None


# ==================== API Info & Health ====================

@api_v1_bp.route('/info', methods=['GET'])
def api_info():
    """Get API information and version
    ---
    tags:
      - System
    responses:
      200:
        description: API information
        schema:
          type: object
          properties:
            api_version:
              type: string
            app_version:
              type: string
            endpoints:
              type: array
            documentation_url:
              type: string
    """
    return jsonify({
        'api_version': 'v1',
        'app_version': current_app.config.get('APP_VERSION', '1.0.0'),
        'documentation_url': '/api/docs',
        'authentication': 'API Token (Bearer or X-API-Key header)',
        'endpoints': {
            'projects': '/api/v1/projects',
            'time_entries': '/api/v1/time-entries',
            'tasks': '/api/v1/tasks',
            'clients': '/api/v1/clients',
            'invoices': '/api/v1/invoices',
            'expenses': '/api/v1/expenses',
            'payments': '/api/v1/payments',
            'mileage': '/api/v1/mileage',
            'per_diems': '/api/v1/per-diems',
            'per_diem_rates': '/api/v1/per-diem-rates',
            'budget_alerts': '/api/v1/budget-alerts',
            'calendar_events': '/api/v1/calendar/events',
            'kanban_columns': '/api/v1/kanban/columns',
            'saved_filters': '/api/v1/saved-filters',
            'time_entry_templates': '/api/v1/time-entry-templates',
            'comments': '/api/v1/comments',
            'recurring_invoices': '/api/v1/recurring-invoices',
            'credit_notes': '/api/v1/credit-notes',
            'client_notes': '/api/v1/clients/<client_id>/notes',
            'project_costs': '/api/v1/projects/<project_id>/costs',
            'tax_rules': '/api/v1/tax-rules',
            'currencies': '/api/v1/currencies',
            'exchange_rates': '/api/v1/exchange-rates',
            'favorites': '/api/v1/users/me/favorites/projects',
            'activities': '/api/v1/activities',
            'audit_logs': '/api/v1/audit-logs',
            'invoice_pdf_templates': '/api/v1/invoice-pdf-templates',
            'invoice_templates': '/api/v1/invoice-templates',
            'users': '/api/v1/users',
            'reports': '/api/v1/reports'
        }
    })


@api_v1_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint
    ---
    tags:
      - System
    responses:
      200:
        description: API is healthy
    """
    return jsonify({'status': 'healthy', 'timestamp': local_now().isoformat()})


# ==================== Projects ====================

@api_v1_bp.route('/projects', methods=['GET'])
@require_api_token('read:projects')
def list_projects():
    """List all projects
    ---
    tags:
      - Projects
    parameters:
      - name: status
        in: query
        type: string
        enum: [active, archived, on_hold]
      - name: client_id
        in: query
        type: integer
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of projects
    """
    query = Project.query
    
    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    # Filter by client
    client_id = request.args.get('client_id', type=int)
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    # Order by name
    query = query.order_by(Project.name)
    
    # Paginate
    result = paginate_query(query)
    
    return jsonify({
        'projects': [p.to_dict() for p in result['items']],
        'pagination': result['pagination']
    })


@api_v1_bp.route('/projects/<int:project_id>', methods=['GET'])
@require_api_token('read:projects')
def get_project(project_id):
    """Get a specific project
    ---
    tags:
      - Projects
    parameters:
      - name: project_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Project details
      404:
        description: Project not found
    """
    project = Project.query.get_or_404(project_id)
    return jsonify({'project': project.to_dict()})


@api_v1_bp.route('/projects', methods=['POST'])
@require_api_token('write:projects')
def create_project():
    """Create a new project
    ---
    tags:
      - Projects
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            description:
              type: string
            client_id:
              type: integer
            hourly_rate:
              type: number
            estimated_hours:
              type: number
            status:
              type: string
              enum: [active, archived, on_hold]
    security:
      - Bearer: []
    responses:
      201:
        description: Project created
      400:
        description: Invalid input
    """
    data = request.get_json() or {}
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Project name is required'}), 400
    
    # Create project
    project = Project(
        name=data['name'],
        description=data.get('description', ''),
        client_id=data.get('client_id'),
        hourly_rate=data.get('hourly_rate', 0.0),
        estimated_hours=data.get('estimated_hours'),
        status=data.get('status', 'active')
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        'message': 'Project created successfully',
        'project': project.to_dict()
    }), 201


@api_v1_bp.route('/projects/<int:project_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:projects')
def update_project(project_id):
    """Update a project
    ---
    tags:
      - Projects
    parameters:
      - name: project_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
    security:
      - Bearer: []
    responses:
      200:
        description: Project updated
      404:
        description: Project not found
    """
    project = Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    
    # Update fields
    if 'name' in data:
        project.name = data['name']
    if 'description' in data:
        project.description = data['description']
    if 'client_id' in data:
        project.client_id = data['client_id']
    if 'hourly_rate' in data:
        project.hourly_rate = data['hourly_rate']
    if 'estimated_hours' in data:
        project.estimated_hours = data['estimated_hours']
    if 'status' in data:
        project.status = data['status']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Project updated successfully',
        'project': project.to_dict()
    })


@api_v1_bp.route('/projects/<int:project_id>', methods=['DELETE'])
@require_api_token('write:projects')
def delete_project(project_id):
    """Delete/archive a project
    ---
    tags:
      - Projects
    parameters:
      - name: project_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Project archived
      404:
        description: Project not found
    """
    project = Project.query.get_or_404(project_id)
    
    # Archive instead of deleting
    project.status = 'archived'
    db.session.commit()
    
    return jsonify({'message': 'Project archived successfully'})


# ==================== Time Entries ====================

@api_v1_bp.route('/time-entries', methods=['GET'])
@require_api_token('read:time_entries')
def list_time_entries():
    """List time entries
    ---
    tags:
      - Time Entries
    parameters:
      - name: project_id
        in: query
        type: integer
      - name: user_id
        in: query
        type: integer
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: billable
        in: query
        type: boolean
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of time entries
    """
    query = TimeEntry.query
    
    # Filter by project
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    # Filter by user (non-admin can only see their own)
    user_id = request.args.get('user_id', type=int)
    if user_id:
        if g.api_user.is_admin or user_id == g.api_user.id:
            query = query.filter_by(user_id=user_id)
        else:
            return jsonify({'error': 'Access denied'}), 403
    else:
        # Default to current user's entries if not admin
        if not g.api_user.is_admin:
            query = query.filter_by(user_id=g.api_user.id)
    
    # Filter by date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        start_dt = parse_datetime(start_date)
        if start_dt:
            query = query.filter(TimeEntry.start_time >= start_dt)
    if end_date:
        end_dt = parse_datetime(end_date)
        if end_dt:
            query = query.filter(TimeEntry.start_time <= end_dt)
    
    # Filter by billable
    billable = request.args.get('billable')
    if billable is not None:
        query = query.filter_by(billable=billable.lower() == 'true')
    
    # Only completed entries by default
    if request.args.get('include_active') != 'true':
        query = query.filter(TimeEntry.end_time.isnot(None))
    
    # Order by start time desc
    query = query.order_by(TimeEntry.start_time.desc())
    
    # Paginate
    result = paginate_query(query)
    
    return jsonify({
        'time_entries': [e.to_dict() for e in result['items']],
        'pagination': result['pagination']
    })


@api_v1_bp.route('/time-entries/<int:entry_id>', methods=['GET'])
@require_api_token('read:time_entries')
def get_time_entry(entry_id):
    """Get a specific time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: entry_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Time entry details
      404:
        description: Time entry not found
    """
    entry = TimeEntry.query.get_or_404(entry_id)
    
    # Check permissions
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({'time_entry': entry.to_dict()})


@api_v1_bp.route('/time-entries', methods=['POST'])
@require_api_token('write:time_entries')
def create_time_entry():
    """Create a new time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - project_id
            - start_time
          properties:
            project_id:
              type: integer
            task_id:
              type: integer
            start_time:
              type: string
              format: date-time
            end_time:
              type: string
              format: date-time
            notes:
              type: string
            tags:
              type: string
            billable:
              type: boolean
    security:
      - Bearer: []
    responses:
      201:
        description: Time entry created
      400:
        description: Invalid input
    """
    data = request.get_json() or {}
    
    # Validate required fields
    if not data.get('project_id'):
        return jsonify({'error': 'project_id is required'}), 400
    if not data.get('start_time'):
        return jsonify({'error': 'start_time is required'}), 400
    
    # Validate project
    project = Project.query.filter_by(id=data['project_id'], status='active').first()
    if not project:
        return jsonify({'error': 'Invalid project'}), 400
    
    # Parse times
    start_time = parse_datetime(data['start_time'])
    if not start_time:
        return jsonify({'error': 'Invalid start_time format'}), 400
    
    end_time = None
    if data.get('end_time'):
        end_time = parse_datetime(data['end_time'])
        if end_time and end_time <= start_time:
            return jsonify({'error': 'end_time must be after start_time'}), 400
    
    # Create entry
    entry = TimeEntry(
        user_id=g.api_user.id,
        project_id=data['project_id'],
        task_id=data.get('task_id'),
        start_time=start_time,
        end_time=end_time,
        notes=data.get('notes'),
        tags=data.get('tags'),
        billable=data.get('billable', True),
        source='api'
    )
    
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({
        'message': 'Time entry created successfully',
        'time_entry': entry.to_dict()
    }), 201


@api_v1_bp.route('/time-entries/<int:entry_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:time_entries')
def update_time_entry(entry_id):
    """Update a time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: entry_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
    security:
      - Bearer: []
    responses:
      200:
        description: Time entry updated
      404:
        description: Time entry not found
    """
    entry = TimeEntry.query.get_or_404(entry_id)
    
    # Check permissions
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json() or {}
    
    # Update fields
    if 'project_id' in data:
        entry.project_id = data['project_id']
    if 'task_id' in data:
        entry.task_id = data['task_id']
    if 'start_time' in data:
        start_time = parse_datetime(data['start_time'])
        if start_time:
            entry.start_time = start_time
    if 'end_time' in data:
        if data['end_time'] is None:
            entry.end_time = None
        else:
            end_time = parse_datetime(data['end_time'])
            if end_time:
                entry.end_time = end_time
    if 'notes' in data:
        entry.notes = data['notes']
    if 'tags' in data:
        entry.tags = data['tags']
    if 'billable' in data:
        entry.billable = data['billable']
    
    entry.updated_at = local_now()
    db.session.commit()
    
    return jsonify({
        'message': 'Time entry updated successfully',
        'time_entry': entry.to_dict()
    })


@api_v1_bp.route('/time-entries/<int:entry_id>', methods=['DELETE'])
@require_api_token('write:time_entries')
def delete_time_entry(entry_id):
    """Delete a time entry
    ---
    tags:
      - Time Entries
    parameters:
      - name: entry_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Time entry deleted
      404:
        description: Time entry not found
    """
    entry = TimeEntry.query.get_or_404(entry_id)
    
    # Check permissions
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Don't allow deletion of active entries
    if entry.is_active:
        return jsonify({'error': 'Cannot delete active time entry'}), 400
    
    db.session.delete(entry)
    db.session.commit()
    
    return jsonify({'message': 'Time entry deleted successfully'})


# ==================== Timer Control ====================

@api_v1_bp.route('/timer/status', methods=['GET'])
@require_api_token('read:time_entries')
def timer_status():
    """Get current timer status for authenticated user
    ---
    tags:
      - Timer
    security:
      - Bearer: []
    responses:
      200:
        description: Timer status
    """
    active_timer = g.api_user.active_timer
    
    if not active_timer:
        return jsonify({
            'active': False,
            'timer': None
        })
    
    return jsonify({
        'active': True,
        'timer': active_timer.to_dict()
    })


@api_v1_bp.route('/timer/start', methods=['POST'])
@require_api_token('write:time_entries')
def start_timer():
    """Start a new timer
    ---
    tags:
      - Timer
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - project_id
          properties:
            project_id:
              type: integer
            task_id:
              type: integer
    security:
      - Bearer: []
    responses:
      201:
        description: Timer started
      400:
        description: Invalid input or timer already running
    """
    data = request.get_json() or {}
    
    # Check if timer already running
    if g.api_user.active_timer:
        return jsonify({'error': 'Timer already running'}), 400
    
    # Validate project
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'error': 'project_id is required'}), 400
    
    project = Project.query.filter_by(id=project_id, status='active').first()
    if not project:
        return jsonify({'error': 'Invalid project'}), 400
    
    # Create timer
    timer = TimeEntry(
        user_id=g.api_user.id,
        project_id=project_id,
        task_id=data.get('task_id'),
        start_time=local_now(),
        source='api'
    )
    
    db.session.add(timer)
    db.session.commit()
    
    return jsonify({
        'message': 'Timer started successfully',
        'timer': timer.to_dict()
    }), 201


@api_v1_bp.route('/timer/stop', methods=['POST'])
@require_api_token('write:time_entries')
def stop_timer():
    """Stop the active timer
    ---
    tags:
      - Timer
    security:
      - Bearer: []
    responses:
      200:
        description: Timer stopped
      400:
        description: No active timer
    """
    active_timer = g.api_user.active_timer
    
    if not active_timer:
        return jsonify({'error': 'No active timer'}), 400
    
    active_timer.stop_timer()
    
    return jsonify({
        'message': 'Timer stopped successfully',
        'time_entry': active_timer.to_dict()
    })


# ==================== Tasks ====================

@api_v1_bp.route('/tasks', methods=['GET'])
@require_api_token('read:tasks')
def list_tasks():
    """List tasks
    ---
    tags:
      - Tasks
    parameters:
      - name: project_id
        in: query
        type: integer
      - name: status
        in: query
        type: string
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of tasks
    """
    query = Task.query
    
    # Filter by project
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    # Order by priority and name
    query = query.order_by(Task.priority.desc(), Task.name)
    
    # Paginate
    result = paginate_query(query)
    
    return jsonify({
        'tasks': [t.to_dict() for t in result['items']],
        'pagination': result['pagination']
    })


@api_v1_bp.route('/tasks/<int:task_id>', methods=['GET'])
@require_api_token('read:tasks')
def get_task(task_id):
    """Get a specific task
    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Task details
      404:
        description: Task not found
    """
    task = Task.query.get_or_404(task_id)
    return jsonify({'task': task.to_dict()})


@api_v1_bp.route('/tasks', methods=['POST'])
@require_api_token('write:tasks')
def create_task():
    """Create a new task
    ---
    tags:
      - Tasks
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - project_id
          properties:
            name:
              type: string
            description:
              type: string
            project_id:
              type: integer
            status:
              type: string
            priority:
              type: integer
    security:
      - Bearer: []
    responses:
      201:
        description: Task created
      400:
        description: Invalid input
    """
    data = request.get_json() or {}
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Task name is required'}), 400
    if not data.get('project_id'):
        return jsonify({'error': 'project_id is required'}), 400
    
    # Create task
    task = Task(
        name=data['name'],
        description=data.get('description'),
        project_id=data['project_id'],
        status=data.get('status', 'todo'),
        priority=data.get('priority', 1)
    )
    
    db.session.add(task)
    db.session.commit()
    
    return jsonify({
        'message': 'Task created successfully',
        'task': task.to_dict()
    }), 201


@api_v1_bp.route('/tasks/<int:task_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:tasks')
def update_task(task_id):
    """Update a task
    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
    security:
      - Bearer: []
    responses:
      200:
        description: Task updated
      404:
        description: Task not found
    """
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or {}
    
    # Update fields
    if 'name' in data:
        task.name = data['name']
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = data['status']
    if 'priority' in data:
        task.priority = data['priority']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Task updated successfully',
        'task': task.to_dict()
    })


@api_v1_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_api_token('write:tasks')
def delete_task(task_id):
    """Delete a task
    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Task deleted
      404:
        description: Task not found
    """
    task = Task.query.get_or_404(task_id)
    
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted successfully'})


# ==================== Clients ====================

@api_v1_bp.route('/clients', methods=['GET'])
@require_api_token('read:clients')
def list_clients():
    """List all clients
    ---
    tags:
      - Clients
    parameters:
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of clients
    """
    query = Client.query.order_by(Client.name)
    
    # Paginate
    result = paginate_query(query)
    
    return jsonify({
        'clients': [c.to_dict() for c in result['items']],
        'pagination': result['pagination']
    })


@api_v1_bp.route('/clients/<int:client_id>', methods=['GET'])
@require_api_token('read:clients')
def get_client(client_id):
    """Get a specific client
    ---
    tags:
      - Clients
    parameters:
      - name: client_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Client details
      404:
        description: Client not found
    """
    client = Client.query.get_or_404(client_id)
    return jsonify({'client': client.to_dict()})


@api_v1_bp.route('/clients', methods=['POST'])
@require_api_token('write:clients')
def create_client():
    """Create a new client
    ---
    tags:
      - Clients
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            email:
              type: string
            company:
              type: string
            phone:
              type: string
    security:
      - Bearer: []
    responses:
      201:
        description: Client created
      400:
        description: Invalid input
    """
    data = request.get_json() or {}
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Client name is required'}), 400
    
    # Create client
    client = Client(
        name=data['name'],
        email=data.get('email'),
        company=data.get('company'),
        phone=data.get('phone')
    )
    
    db.session.add(client)
    db.session.commit()
    
    return jsonify({
        'message': 'Client created successfully',
        'client': client.to_dict()
    }), 201


# ==================== Invoices ====================

@api_v1_bp.route('/invoices', methods=['GET'])
@require_api_token('read:invoices')
def list_invoices():
    """List invoices
    ---
    tags:
      - Invoices
    parameters:
      - name: status
        in: query
        type: string
      - name: client_id
        in: query
        type: integer
      - name: project_id
        in: query
        type: integer
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of invoices
    """
    query = Invoice.query
    status = request.args.get('status')
    if status:
        query = query.filter(Invoice.status == status)
    client_id = request.args.get('client_id', type=int)
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter(Invoice.project_id == project_id)
    query = query.order_by(Invoice.created_at.desc())
    result = paginate_query(query)
    return jsonify({
        'invoices': [inv.to_dict() for inv in result['items']],
        'pagination': result['pagination']
    })


@api_v1_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@require_api_token('read:invoices')
def get_invoice(invoice_id):
    """Get invoice by id
    ---
    tags:
      - Invoices
    security:
      - Bearer: []
    responses:
      200:
        description: Invoice
      404:
        description: Not found
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    return jsonify({'invoice': invoice.to_dict()})


@api_v1_bp.route('/invoices', methods=['POST'])
@require_api_token('write:invoices')
def create_invoice():
    """Create a new invoice
    ---
    tags:
      - Invoices
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - project_id
            - client_id
            - client_name
            - due_date
          properties:
            invoice_number: { type: string }
            project_id: { type: integer }
            client_id: { type: integer }
            client_name: { type: string }
            client_email: { type: string }
            client_address: { type: string }
            due_date: { type: string, format: date }
            tax_rate: { type: number }
            currency_code: { type: string }
            notes: { type: string }
            terms: { type: string }
    security:
      - Bearer: []
    responses:
      201:
        description: Invoice created
      400:
        description: Invalid input
    """
    data = request.get_json() or {}
    # Validate required fields
    required = ['project_id', 'client_id', 'client_name', 'due_date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    # Validate foreign keys
    project = Project.query.get(data['project_id'])
    client = Client.query.get(data['client_id'])
    if not project or not client:
        return jsonify({'error': 'Invalid project_id or client_id'}), 400
    due_dt = _parse_date(data.get('due_date'))
    if not due_dt:
        return jsonify({'error': 'Invalid due_date format, expected YYYY-MM-DD'}), 400
    invoice_number = data.get('invoice_number') or Invoice.generate_invoice_number()
    invoice = Invoice(
        invoice_number=invoice_number,
        project_id=project.id,
        client_name=data['client_name'],
        client_id=client.id,
        due_date=due_dt,
        created_by=g.api_user.id,
        client_email=data.get('client_email'),
        client_address=data.get('client_address'),
        notes=data.get('notes'),
        terms=data.get('terms'),
        tax_rate=data.get('tax_rate', 0),
        currency_code=data.get('currency_code', 'EUR'),
    )
    db.session.add(invoice)
    db.session.commit()
    return jsonify({'message': 'Invoice created successfully', 'invoice': invoice.to_dict()}), 201


@api_v1_bp.route('/invoices/<int:invoice_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:invoices')
def update_invoice(invoice_id):
    """Update an invoice
    ---
    tags:
      - Invoices
    security:
      - Bearer: []
    responses:
      200:
        description: Invoice updated
      404:
        description: Not found
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    data = request.get_json() or {}
    # Update basic fields if present
    for field in ('client_name', 'client_email', 'client_address', 'notes', 'terms', 'status', 'currency_code'):
        if field in data:
            setattr(invoice, field, data[field])
    if 'due_date' in data:
        parsed = _parse_date(data['due_date'])
        if parsed:
            invoice.due_date = parsed
    if 'tax_rate' in data:
        try:
            invoice.tax_rate = float(data['tax_rate'])
        except Exception:
            pass
    if 'amount_paid' in data:
        try:
            from decimal import Decimal
            invoice.amount_paid = Decimal(str(data['amount_paid']))
            invoice.update_payment_status()
        except Exception:
            pass
    db.session.commit()
    return jsonify({'message': 'Invoice updated successfully', 'invoice': invoice.to_dict()})


@api_v1_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@require_api_token('write:invoices')
def delete_invoice(invoice_id):
    """Cancel an invoice (soft-delete)
    ---
    tags:
      - Invoices
    security:
      - Bearer: []
    responses:
      200:
        description: Invoice cancelled
      404:
        description: Not found
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Invoice cancelled successfully'})


# ==================== Expenses ====================

@api_v1_bp.route('/expenses', methods=['GET'])
@require_api_token('read:expenses')
def list_expenses():
    """List expenses
    ---
    tags:
      - Expenses
    parameters:
      - name: user_id
        in: query
        type: integer
      - name: project_id
        in: query
        type: integer
      - name: client_id
        in: query
        type: integer
      - name: status
        in: query
        type: string
      - name: category
        in: query
        type: string
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of expenses
    """
    query = Expense.query
    # Restrict by user if not admin
    user_id = request.args.get('user_id', type=int)
    if user_id:
        if g.api_user.is_admin or user_id == g.api_user.id:
            query = query.filter(Expense.user_id == user_id)
        else:
            return jsonify({'error': 'Access denied'}), 403
    else:
        if not g.api_user.is_admin:
            query = query.filter(Expense.user_id == g.api_user.id)
    # Other filters
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter(Expense.project_id == project_id)
    client_id = request.args.get('client_id', type=int)
    if client_id:
        query = query.filter(Expense.client_id == client_id)
    status = request.args.get('status')
    if status:
        query = query.filter(Expense.status == status)
    category = request.args.get('category')
    if category:
        query = query.filter(Expense.category == category)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    query = query.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
    result = paginate_query(query)
    return jsonify({
        'expenses': [e.to_dict() for e in result['items']],
        'pagination': result['pagination']
    })


@api_v1_bp.route('/expenses/<int:expense_id>', methods=['GET'])
@require_api_token('read:expenses')
def get_expense(expense_id):
    """Get an expense
    ---
    tags:
      - Expenses
    security:
      - Bearer: []
    responses:
      200:
        description: Expense
      404:
        description: Not found
    """
    expense = Expense.query.get_or_404(expense_id)
    if not g.api_user.is_admin and expense.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'expense': expense.to_dict()})


@api_v1_bp.route('/expenses', methods=['POST'])
@require_api_token('write:expenses')
def create_expense():
    """Create a new expense
    ---
    tags:
      - Expenses
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - title
            - category
            - amount
            - expense_date
          properties:
            title: { type: string }
            description: { type: string }
            category: { type: string }
            amount: { type: number }
            currency_code: { type: string }
            expense_date: { type: string, format: date }
            project_id: { type: integer }
            client_id: { type: integer }
            billable: { type: boolean }
            reimbursable: { type: boolean }
            payment_method: { type: string }
            payment_date: { type: string, format: date }
            tags: { type: string }
    security:
      - Bearer: []
    responses:
      201:
        description: Expense created
      400:
        description: Invalid input
    """
    data = request.get_json() or {}
    required = ['title', 'category', 'amount', 'expense_date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    exp_date = _parse_date(data.get('expense_date'))
    if not exp_date:
        return jsonify({'error': 'Invalid expense_date format, expected YYYY-MM-DD'}), 400
    pay_date = _parse_date(data.get('payment_date'))
    from decimal import Decimal
    try:
        amount = Decimal(str(data['amount']))
    except Exception:
        return jsonify({'error': 'Invalid amount'}), 400
    expense = Expense(
        user_id=g.api_user.id,
        title=data['title'],
        category=data['category'],
        amount=amount,
        expense_date=exp_date,
        description=data.get('description'),
        project_id=data.get('project_id'),
        client_id=data.get('client_id'),
        currency_code=data.get('currency_code', 'EUR'),
        tax_amount=data.get('tax_amount', 0),
        tax_rate=data.get('tax_rate', 0),
        payment_method=data.get('payment_method'),
        payment_date=pay_date,
        billable=data.get('billable', False),
        reimbursable=data.get('reimbursable', True),
        tags=data.get('tags'),
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify({'message': 'Expense created successfully', 'expense': expense.to_dict()}), 201


@api_v1_bp.route('/expenses/<int:expense_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:expenses')
def update_expense(expense_id):
    """Update an expense
    ---
    tags:
      - Expenses
    security:
      - Bearer: []
    responses:
      200:
        description: Expense updated
      404:
        description: Not found
    """
    expense = Expense.query.get_or_404(expense_id)
    if not g.api_user.is_admin and expense.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    for field in ('title', 'description', 'category', 'currency_code', 'payment_method', 'status', 'tags'):
        if field in data:
            setattr(expense, field, data[field])
    if 'amount' in data:
        try:
            from decimal import Decimal
            expense.amount = Decimal(str(data['amount']))
        except Exception:
            pass
    if 'expense_date' in data:
        parsed = _parse_date(data['expense_date'])
        if parsed:
            expense.expense_date = parsed
    if 'payment_date' in data:
        parsed = _parse_date(data['payment_date'])
        expense.payment_date = parsed
    for bfield in ('billable', 'reimbursable', 'reimbursed', 'invoiced'):
        if bfield in data:
            setattr(expense, bfield, bool(data[bfield]))
    db.session.commit()
    return jsonify({'message': 'Expense updated successfully', 'expense': expense.to_dict()})


@api_v1_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@require_api_token('write:expenses')
def delete_expense(expense_id):
    """Reject an expense (soft-delete)
    ---
    tags:
      - Expenses
    security:
      - Bearer: []
    responses:
      200:
        description: Expense rejected
      404:
        description: Not found
    """
    expense = Expense.query.get_or_404(expense_id)
    if not g.api_user.is_admin and expense.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    expense.status = 'rejected'
    db.session.commit()
    return jsonify({'message': 'Expense rejected successfully'})


# ==================== Payments ====================

@api_v1_bp.route('/payments', methods=['GET'])
@require_api_token('read:payments')
def list_payments():
    """List payments
    ---
    tags:
      - Payments
    parameters:
      - name: invoice_id
        in: query
        type: integer
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of payments
    """
    query = Payment.query
    invoice_id = request.args.get('invoice_id', type=int)
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    query = query.order_by(Payment.created_at.desc())
    result = paginate_query(query)
    return jsonify({'payments': [p.to_dict() for p in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/payments/<int:payment_id>', methods=['GET'])
@require_api_token('read:payments')
def get_payment(payment_id):
    """Get a payment
    ---
    tags:
      - Payments
    security:
      - Bearer: []
    responses:
      200:
        description: Payment
    """
    payment = Payment.query.get_or_404(payment_id)
    return jsonify({'payment': payment.to_dict()})


@api_v1_bp.route('/payments', methods=['POST'])
@require_api_token('write:payments')
def create_payment():
    """Create a payment
    ---
    tags:
      - Payments
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [invoice_id, amount]
          properties:
            invoice_id: { type: integer }
            amount: { type: number }
            currency: { type: string }
            payment_date: { type: string, format: date }
            method: { type: string }
            reference: { type: string }
            notes: { type: string }
    security:
      - Bearer: []
    responses:
      201:
        description: Payment created
    """
    data = request.get_json() or {}
    required = ['invoice_id', 'amount']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    inv = Invoice.query.get(data['invoice_id'])
    if not inv:
        return jsonify({'error': 'Invalid invoice_id'}), 400
    from decimal import Decimal
    try:
        amount = Decimal(str(data['amount']))
    except Exception:
        return jsonify({'error': 'Invalid amount'}), 400
    pay_date = _parse_date(data.get('payment_date'))
    payment = Payment(
        invoice_id=inv.id,
        amount=amount,
        currency=data.get('currency', 'EUR'),
        payment_date=pay_date or None,
        method=data.get('method'),
        reference=data.get('reference'),
        notes=data.get('notes'),
        received_by=getattr(g.api_user, 'id', None),
    )
    payment.calculate_net_amount()
    db.session.add(payment)
    db.session.commit()
    return jsonify({'message': 'Payment created successfully', 'payment': payment.to_dict()}), 201


@api_v1_bp.route('/payments/<int:payment_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:payments')
def update_payment(payment_id):
    """Update a payment
    ---
    tags:
      - Payments
    security:
      - Bearer: []
    responses:
      200:
        description: Payment updated
    """
    payment = Payment.query.get_or_404(payment_id)
    data = request.get_json() or {}
    for field in ('currency', 'method', 'reference', 'notes', 'status'):
        if field in data:
            setattr(payment, field, data[field])
    if 'amount' in data:
        try:
            from decimal import Decimal
            payment.amount = Decimal(str(data['amount']))
        except Exception:
            pass
    if 'payment_date' in data:
        parsed = _parse_date(data['payment_date'])
        payment.payment_date = parsed
    payment.calculate_net_amount()
    db.session.commit()
    return jsonify({'message': 'Payment updated successfully', 'payment': payment.to_dict()})


@api_v1_bp.route('/payments/<int:payment_id>', methods=['DELETE'])
@require_api_token('write:payments')
def delete_payment(payment_id):
    """Delete a payment
    ---
    tags:
      - Payments
    security:
      - Bearer: []
    responses:
      200:
        description: Payment deleted
    """
    payment = Payment.query.get_or_404(payment_id)
    db.session.delete(payment)
    db.session.commit()
    return jsonify({'message': 'Payment deleted successfully'})


# ==================== Mileage ====================

@api_v1_bp.route('/mileage', methods=['GET'])
@require_api_token('read:mileage')
def list_mileage():
    """List mileage entries (non-admin see own only)
    ---
    tags:
      - Mileage
    parameters:
      - name: user_id
        in: query
        type: integer
      - name: project_id
        in: query
        type: integer
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of mileage entries
    """
    query = Mileage.query
    user_id = request.args.get('user_id', type=int)
    if user_id:
        if g.api_user.is_admin or user_id == g.api_user.id:
            query = query.filter(Mileage.user_id == user_id)
        else:
            return jsonify({'error': 'Access denied'}), 403
    else:
        if not g.api_user.is_admin:
            query = query.filter(Mileage.user_id == g.api_user.id)
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter(Mileage.project_id == project_id)
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))
    if start_date:
        query = query.filter(Mileage.trip_date >= start_date)
    if end_date:
        query = query.filter(Mileage.trip_date <= end_date)
    query = query.order_by(Mileage.trip_date.desc(), Mileage.created_at.desc())
    result = paginate_query(query)
    return jsonify({'mileage': [m.to_dict() for m in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/mileage/<int:entry_id>', methods=['GET'])
@require_api_token('read:mileage')
def get_mileage(entry_id):
    """Get a mileage entry
    ---
    tags:
      - Mileage
    security:
      - Bearer: []
    """
    entry = Mileage.query.get_or_404(entry_id)
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'mileage': entry.to_dict()})


@api_v1_bp.route('/mileage', methods=['POST'])
@require_api_token('write:mileage')
def create_mileage():
    """Create a mileage entry
    ---
    tags:
      - Mileage
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [trip_date, purpose, start_location, end_location, distance_km, rate_per_km]
          properties:
            trip_date: { type: string, format: date }
            purpose: { type: string }
            start_location: { type: string }
            end_location: { type: string }
            distance_km: { type: number }
            rate_per_km: { type: number }
            project_id: { type: integer }
            client_id: { type: integer }
            is_round_trip: { type: boolean }
    """
    data = request.get_json() or {}
    required = ['trip_date', 'purpose', 'start_location', 'end_location', 'distance_km', 'rate_per_km']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    trip_date = _parse_date(data.get('trip_date'))
    if not trip_date:
        return jsonify({'error': 'Invalid trip_date format, expected YYYY-MM-DD'}), 400
    from decimal import Decimal
    try:
        distance_km = Decimal(str(data['distance_km']))
        rate_per_km = Decimal(str(data['rate_per_km']))
    except Exception:
        return jsonify({'error': 'Invalid distance_km or rate_per_km'}), 400
    entry = Mileage(
        user_id=g.api_user.id,
        trip_date=trip_date,
        purpose=data['purpose'],
        start_location=data['start_location'],
        end_location=data['end_location'],
        distance_km=distance_km,
        rate_per_km=rate_per_km,
        project_id=data.get('project_id'),
        client_id=data.get('client_id'),
        is_round_trip=bool(data.get('is_round_trip', False)),
        description=data.get('description'),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({'message': 'Mileage entry created successfully', 'mileage': entry.to_dict()}), 201


@api_v1_bp.route('/mileage/<int:entry_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:mileage')
def update_mileage(entry_id):
    """Update a mileage entry
    ---
    tags:
      - Mileage
    """
    entry = Mileage.query.get_or_404(entry_id)
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    for field in ('purpose', 'start_location', 'end_location', 'description', 'vehicle_type', 'vehicle_description', 'license_plate', 'currency_code', 'status', 'notes'):
        if field in data:
            setattr(entry, field, data[field])
    if 'trip_date' in data:
        parsed = _parse_date(data['trip_date'])
        if parsed:
            entry.trip_date = parsed
    for numfield in ('distance_km', 'rate_per_km', 'start_odometer', 'end_odometer'):
        if numfield in data:
            try:
                from decimal import Decimal
                setattr(entry, numfield, Decimal(str(data[numfield])))
            except Exception:
                pass
    if 'is_round_trip' in data:
        entry.is_round_trip = bool(data['is_round_trip'])
    db.session.commit()
    return jsonify({'message': 'Mileage entry updated successfully', 'mileage': entry.to_dict()})


@api_v1_bp.route('/mileage/<int:entry_id>', methods=['DELETE'])
@require_api_token('write:mileage')
def delete_mileage(entry_id):
    """Reject a mileage entry
    ---
    tags:
      - Mileage
    """
    entry = Mileage.query.get_or_404(entry_id)
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    entry.status = 'rejected'
    db.session.commit()
    return jsonify({'message': 'Mileage entry rejected successfully'})


# ==================== Per Diem ====================

@api_v1_bp.route('/per-diems', methods=['GET'])
@require_api_token('read:per_diem')
def list_per_diems():
    """List per diem claims (non-admin see own only)
    ---
    tags:
      - PerDiem
    """
    query = PerDiem.query
    if not g.api_user.is_admin:
        query = query.filter(PerDiem.user_id == g.api_user.id)
    result = paginate_query(query.order_by(PerDiem.start_date.desc()))
    return jsonify({'per_diems': [p.to_dict() for p in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/per-diems/<int:pd_id>', methods=['GET'])
@require_api_token('read:per_diem')
def get_per_diem(pd_id):
    """Get a per diem claim
    ---
    tags:
      - PerDiem
    """
    pd = PerDiem.query.get_or_404(pd_id)
    if not g.api_user.is_admin and pd.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'per_diem': pd.to_dict()})


@api_v1_bp.route('/per-diems', methods=['POST'])
@require_api_token('write:per_diem')
def create_per_diem():
    """Create a per diem claim
    ---
    tags:
      - PerDiem
    """
    data = request.get_json() or {}
    required = ['trip_purpose', 'start_date', 'end_date', 'country', 'full_day_rate', 'half_day_rate']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    sdate = _parse_date(data.get('start_date'))
    edate = _parse_date(data.get('end_date'))
    if not sdate or not edate or edate < sdate:
        return jsonify({'error': 'Invalid date range'}), 400
    from decimal import Decimal
    try:
        fdr = Decimal(str(data['full_day_rate']))
        hdr = Decimal(str(data['half_day_rate']))
    except Exception:
        return jsonify({'error': 'Invalid rates'}), 400
    pd = PerDiem(
        user_id=g.api_user.id,
        trip_purpose=data['trip_purpose'],
        start_date=sdate,
        end_date=edate,
        country=data['country'],
        full_day_rate=fdr,
        half_day_rate=hdr,
        city=data.get('city'),
        description=data.get('description'),
        currency_code=data.get('currency_code', 'EUR'),
        full_days=data.get('full_days', 0),
        half_days=data.get('half_days', 0),
        breakfast_provided=data.get('breakfast_provided', 0),
        lunch_provided=data.get('lunch_provided', 0),
        dinner_provided=data.get('dinner_provided', 0),
    )
    pd.recalculate_amount()
    db.session.add(pd)
    db.session.commit()
    return jsonify({'message': 'Per diem created successfully', 'per_diem': pd.to_dict()}), 201


@api_v1_bp.route('/per-diems/<int:pd_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:per_diem')
def update_per_diem(pd_id):
    """Update a per diem claim
    ---
    tags:
      - PerDiem
    """
    pd = PerDiem.query.get_or_404(pd_id)
    if not g.api_user.is_admin and pd.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    for field in ('trip_purpose', 'description', 'country', 'city', 'currency_code', 'status', 'notes'):
        if field in data:
            setattr(pd, field, data[field])
    for numfield in ('full_days', 'half_days', 'breakfast_provided', 'lunch_provided', 'dinner_provided'):
        if numfield in data:
            try:
                setattr(pd, numfield, int(data[numfield]))
            except Exception:
                pass
    for ratefield in ('full_day_rate', 'half_day_rate', 'breakfast_deduction', 'lunch_deduction', 'dinner_deduction'):
        if ratefield in data:
            try:
                from decimal import Decimal
                setattr(pd, ratefield, Decimal(str(data[ratefield])))
            except Exception:
                pass
    if 'start_date' in data:
        parsed = _parse_date(data['start_date'])
        if parsed:
            pd.start_date = parsed
    if 'end_date' in data:
        parsed = _parse_date(data['end_date'])
        if parsed:
            pd.end_date = parsed
    pd.recalculate_amount()
    db.session.commit()
    return jsonify({'message': 'Per diem updated successfully', 'per_diem': pd.to_dict()})


@api_v1_bp.route('/per-diems/<int:pd_id>', methods=['DELETE'])
@require_api_token('write:per_diem')
def delete_per_diem(pd_id):
    """Reject a per diem claim
    ---
    tags:
      - PerDiem
    """
    pd = PerDiem.query.get_or_404(pd_id)
    if not g.api_user.is_admin and pd.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    pd.status = 'rejected'
    db.session.commit()
    return jsonify({'message': 'Per diem rejected successfully'})


@api_v1_bp.route('/per-diem-rates', methods=['GET'])
@require_api_token('read:per_diem')
def list_per_diem_rates():
    """List per diem rates
    ---
    tags:
      - PerDiemRates
    """
    query = PerDiemRate.query.filter(PerDiemRate.is_active == True)
    result = paginate_query(query.order_by(PerDiemRate.country.asc(), PerDiemRate.city.asc()))
    return jsonify({'rates': [r.to_dict() for r in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/per-diem-rates', methods=['POST'])
@require_api_token('admin:all')
def create_per_diem_rate():
    """Create a per diem rate (admin)
    ---
    tags:
      - PerDiemRates
    """
    data = request.get_json() or {}
    required = ['country', 'full_day_rate', 'half_day_rate', 'effective_from']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    eff_from = _parse_date(data.get('effective_from'))
    eff_to = _parse_date(data.get('effective_to'))
    from decimal import Decimal
    try:
        fdr = Decimal(str(data['full_day_rate']))
        hdr = Decimal(str(data['half_day_rate']))
    except Exception:
        return jsonify({'error': 'Invalid rates'}), 400
    rate = PerDiemRate(
        country=data['country'],
        full_day_rate=fdr,
        half_day_rate=hdr,
        effective_from=eff_from,
        effective_to=eff_to,
        city=data.get('city'),
        currency_code=data.get('currency_code', 'EUR'),
        breakfast_rate=data.get('breakfast_rate'),
        lunch_rate=data.get('lunch_rate'),
        dinner_rate=data.get('dinner_rate'),
        incidental_rate=data.get('incidental_rate'),
        is_active=bool(data.get('is_active', True)),
        notes=data.get('notes'),
    )
    db.session.add(rate)
    db.session.commit()
    return jsonify({'message': 'Per diem rate created successfully', 'rate': rate.to_dict()}), 201


# ==================== Budget Alerts ====================

@api_v1_bp.route('/budget-alerts', methods=['GET'])
@require_api_token('read:budget_alerts')
def list_budget_alerts():
    """List budget alerts
    ---
    tags:
      - BudgetAlerts
    """
    query = BudgetAlert.query
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter(BudgetAlert.project_id == project_id)
    result = paginate_query(query.order_by(BudgetAlert.created_at.desc()))
    return jsonify({'alerts': [a.to_dict() for a in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/budget-alerts', methods=['POST'])
@require_api_token('admin:all')
def create_budget_alert():
    """Create a budget alert (admin)
    ---
    tags:
      - BudgetAlerts
    """
    data = request.get_json() or {}
    required = ['project_id', 'alert_type', 'budget_consumed_percent', 'budget_amount', 'consumed_amount', 'message']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    alert = BudgetAlert(
        project_id=data['project_id'],
        alert_type=data['alert_type'],
        alert_level=data.get('alert_level', 'info'),
        budget_consumed_percent=data['budget_consumed_percent'],
        budget_amount=data['budget_amount'],
        consumed_amount=data['consumed_amount'],
        message=data['message'],
    )
    db.session.add(alert)
    db.session.commit()
    return jsonify({'message': 'Budget alert created successfully', 'alert': alert.to_dict()}), 201


@api_v1_bp.route('/budget-alerts/<int:alert_id>/ack', methods=['POST'])
@require_api_token('write:budget_alerts')
def acknowledge_budget_alert(alert_id):
    """Acknowledge a budget alert
    ---
    tags:
      - BudgetAlerts
    """
    alert = BudgetAlert.query.get_or_404(alert_id)
    alert.acknowledge(g.api_user.id)
    return jsonify({'message': 'Alert acknowledged'})


# ==================== Calendar Events ====================

@api_v1_bp.route('/calendar/events', methods=['GET'])
@require_api_token('read:calendar')
def list_calendar_events():
    """List calendar events for current user
    ---
    tags:
      - Calendar
    parameters:
      - name: start
        in: query
        type: string
      - name: end
        in: query
        type: string
    """
    start = request.args.get('start')
    end = request.args.get('end')
    start_dt = parse_datetime(start) if start else None
    end_dt = parse_datetime(end) if end else None
    query = CalendarEvent.query.filter(CalendarEvent.user_id == g.api_user.id)
    if start_dt:
        query = query.filter(CalendarEvent.start_time >= start_dt)
    if end_dt:
        query = query.filter(CalendarEvent.start_time <= end_dt)
    events = query.order_by(CalendarEvent.start_time.asc()).all()
    return jsonify({'events': [e.to_dict() for e in events]})


@api_v1_bp.route('/calendar/events/<int:event_id>', methods=['GET'])
@require_api_token('read:calendar')
def get_calendar_event(event_id):
    """Get calendar event
    ---
    tags:
      - Calendar
    """
    ev = CalendarEvent.query.get_or_404(event_id)
    if not g.api_user.is_admin and ev.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'event': ev.to_dict()})


@api_v1_bp.route('/calendar/events', methods=['POST'])
@require_api_token('write:calendar')
def create_calendar_event():
    """Create calendar event
    ---
    tags:
      - Calendar
    """
    data = request.get_json() or {}
    required = ['title', 'start_time', 'end_time']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    start_dt = parse_datetime(data['start_time'])
    end_dt = parse_datetime(data['end_time'])
    if not start_dt or not end_dt or end_dt <= start_dt:
        return jsonify({'error': 'Invalid start/end time'}), 400
    ev = CalendarEvent(
        user_id=g.api_user.id,
        title=data['title'],
        start_time=start_dt,
        end_time=end_dt,
        description=data.get('description'),
        all_day=bool(data.get('all_day', False)),
        location=data.get('location'),
        project_id=data.get('project_id'),
        task_id=data.get('task_id'),
        client_id=data.get('client_id'),
        event_type=data.get('event_type', 'event'),
        reminder_minutes=data.get('reminder_minutes'),
        color=data.get('color'),
        is_private=bool(data.get('is_private', False)),
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify({'message': 'Event created successfully', 'event': ev.to_dict()}), 201


@api_v1_bp.route('/calendar/events/<int:event_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:calendar')
def update_calendar_event(event_id):
    """Update calendar event
    ---
    tags:
      - Calendar
    """
    ev = CalendarEvent.query.get_or_404(event_id)
    if not g.api_user.is_admin and ev.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    for field in ('title', 'description', 'location', 'event_type', 'color', 'is_private', 'reminder_minutes'):
        if field in data:
            setattr(ev, field, data[field])
    if 'start_time' in data:
        parsed = parse_datetime(data['start_time'])
        if parsed:
            ev.start_time = parsed
    if 'end_time' in data:
        parsed = parse_datetime(data['end_time'])
        if parsed:
            ev.end_time = parsed
    db.session.commit()
    return jsonify({'message': 'Event updated successfully', 'event': ev.to_dict()})


@api_v1_bp.route('/calendar/events/<int:event_id>', methods=['DELETE'])
@require_api_token('write:calendar')
def delete_calendar_event(event_id):
    """Delete calendar event
    ---
    tags:
      - Calendar
    """
    ev = CalendarEvent.query.get_or_404(event_id)
    if not g.api_user.is_admin and ev.user_id != g.api_user.id:
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(ev)
    db.session.commit()
    return jsonify({'message': 'Event deleted successfully'})


# ==================== Kanban Columns ====================

@api_v1_bp.route('/kanban/columns', methods=['GET'])
@require_api_token('read:tasks')
def list_kanban_columns():
    """List kanban columns
    ---
    tags:
      - Kanban
    parameters:
      - name: project_id
        in: query
        type: integer
    """
    project_id = request.args.get('project_id', type=int)
    cols = KanbanColumn.get_all_columns(project_id=project_id)
    return jsonify({'columns': [c.to_dict() for c in cols]})


@api_v1_bp.route('/kanban/columns', methods=['POST'])
@require_api_token('write:tasks')
def create_kanban_column():
    """Create kanban column
    ---
    tags:
      - Kanban
    """
    data = request.get_json() or {}
    required = ['key', 'label']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    col = KanbanColumn(
        key=data['key'],
        label=data['label'],
        icon=data.get('icon', 'fas fa-circle'),
        color=data.get('color', 'secondary'),
        position=data.get('position', 0),
        is_active=bool(data.get('is_active', True)),
        is_system=bool(data.get('is_system', False)),
        is_complete_state=bool(data.get('is_complete_state', False)),
        project_id=data.get('project_id'),
    )
    db.session.add(col)
    db.session.commit()
    return jsonify({'message': 'Column created successfully', 'column': col.to_dict()}), 201


@api_v1_bp.route('/kanban/columns/<int:col_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:tasks')
def update_kanban_column(col_id):
    """Update kanban column
    ---
    tags:
      - Kanban
    """
    col = KanbanColumn.query.get_or_404(col_id)
    data = request.get_json() or {}
    for field in ('key', 'label', 'icon', 'color', 'position', 'is_active', 'is_complete_state'):
        if field in data:
            setattr(col, field, data[field])
    db.session.commit()
    return jsonify({'message': 'Column updated successfully', 'column': col.to_dict()})


@api_v1_bp.route('/kanban/columns/<int:col_id>', methods=['DELETE'])
@require_api_token('write:tasks')
def delete_kanban_column(col_id):
    """Delete kanban column
    ---
    tags:
      - Kanban
    """
    col = KanbanColumn.query.get_or_404(col_id)
    if col.is_system:
        return jsonify({'error': 'Cannot delete system column'}), 400
    db.session.delete(col)
    db.session.commit()
    return jsonify({'message': 'Column deleted successfully'})


@api_v1_bp.route('/kanban/columns/reorder', methods=['POST'])
@require_api_token('write:tasks')
def reorder_kanban_columns():
    """Reorder kanban columns
    ---
    tags:
      - Kanban
    """
    data = request.get_json() or {}
    ids = data.get('column_ids') or []
    project_id = data.get('project_id')
    if not isinstance(ids, list) or not ids:
        return jsonify({'error': 'column_ids must be a non-empty list'}), 400
    KanbanColumn.reorder_columns(ids, project_id=project_id)
    return jsonify({'message': 'Columns reordered successfully'})


# ==================== Saved Filters ====================

@api_v1_bp.route('/saved-filters', methods=['GET'])
@require_api_token('read:filters')
def list_saved_filters():
    """List saved filters for current user
    ---
    tags:
      - SavedFilters
    """
    query = SavedFilter.query.filter(SavedFilter.user_id == g.api_user.id)
    result = paginate_query(query.order_by(SavedFilter.created_at.desc()))
    return jsonify({'filters': [f.to_dict() for f in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/saved-filters/<int:filter_id>', methods=['GET'])
@require_api_token('read:filters')
def get_saved_filter(filter_id):
    """Get saved filter
    ---
    tags:
      - SavedFilters
    """
    sf = SavedFilter.query.get_or_404(filter_id)
    if sf.user_id != g.api_user.id and not (sf.is_shared or g.api_user.is_admin):
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'filter': sf.to_dict()})


@api_v1_bp.route('/saved-filters', methods=['POST'])
@require_api_token('write:filters')
def create_saved_filter():
    """Create saved filter
    ---
    tags:
      - SavedFilters
    """
    data = request.get_json() or {}
    required = ['name', 'scope', 'payload']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    sf = SavedFilter(
        user_id=g.api_user.id,
        name=data['name'],
        scope=data['scope'],
        payload=data['payload'],
        is_shared=bool(data.get('is_shared', False)),
    )
    db.session.add(sf)
    db.session.commit()
    return jsonify({'message': 'Saved filter created successfully', 'filter': sf.to_dict()}), 201


@api_v1_bp.route('/saved-filters/<int:filter_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:filters')
def update_saved_filter(filter_id):
    """Update saved filter
    ---
    tags:
      - SavedFilters
    """
    sf = SavedFilter.query.get_or_404(filter_id)
    if sf.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    for field in ('name', 'scope', 'payload', 'is_shared'):
        if field in data:
            setattr(sf, field, data[field])
    db.session.commit()
    return jsonify({'message': 'Saved filter updated successfully', 'filter': sf.to_dict()})


@api_v1_bp.route('/saved-filters/<int:filter_id>', methods=['DELETE'])
@require_api_token('write:filters')
def delete_saved_filter(filter_id):
    """Delete saved filter
    ---
    tags:
      - SavedFilters
    """
    sf = SavedFilter.query.get_or_404(filter_id)
    if sf.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(sf)
    db.session.commit()
    return jsonify({'message': 'Saved filter deleted successfully'})


# ==================== Time Entry Templates ====================

@api_v1_bp.route('/time-entry-templates', methods=['GET'])
@require_api_token('read:time_entries')
def list_time_entry_templates():
    """List time entry templates for current user
    ---
    tags:
      - TimeEntryTemplates
    """
    query = TimeEntryTemplate.query.filter(TimeEntryTemplate.user_id == g.api_user.id)
    result = paginate_query(query.order_by(TimeEntryTemplate.created_at.desc()))
    return jsonify({'templates': [t.to_dict() for t in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/time-entry-templates/<int:tpl_id>', methods=['GET'])
@require_api_token('read:time_entries')
def get_time_entry_template(tpl_id):
    """Get time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    tpl = TimeEntryTemplate.query.get_or_404(tpl_id)
    if tpl.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'template': tpl.to_dict()})


@api_v1_bp.route('/time-entry-templates', methods=['POST'])
@require_api_token('write:time_entries')
def create_time_entry_template():
    """Create time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    data = request.get_json() or {}
    required = ['name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    tpl = TimeEntryTemplate(
        user_id=g.api_user.id,
        name=data['name'],
        description=data.get('description'),
        project_id=data.get('project_id'),
        task_id=data.get('task_id'),
        default_duration_minutes=data.get('default_duration_minutes'),
        default_notes=data.get('default_notes'),
        tags=data.get('tags'),
        billable=bool(data.get('billable', True)),
    )
    db.session.add(tpl)
    db.session.commit()
    return jsonify({'message': 'Template created successfully', 'template': tpl.to_dict()}), 201


@api_v1_bp.route('/time-entry-templates/<int:tpl_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:time_entries')
def update_time_entry_template(tpl_id):
    """Update time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    tpl = TimeEntryTemplate.query.get_or_404(tpl_id)
    if tpl.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    for field in ('name', 'description', 'project_id', 'task_id', 'default_duration_minutes', 'default_notes', 'tags', 'billable'):
        if field in data:
            setattr(tpl, field, data[field])
    db.session.commit()
    return jsonify({'message': 'Template updated successfully', 'template': tpl.to_dict()})


@api_v1_bp.route('/time-entry-templates/<int:tpl_id>', methods=['DELETE'])
@require_api_token('write:time_entries')
def delete_time_entry_template(tpl_id):
    """Delete time entry template
    ---
    tags:
      - TimeEntryTemplates
    """
    tpl = TimeEntryTemplate.query.get_or_404(tpl_id)
    if tpl.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(tpl)
    db.session.commit()
    return jsonify({'message': 'Template deleted successfully'})


# ==================== Comments ====================

@api_v1_bp.route('/comments', methods=['GET'])
@require_api_token('read:comments')
def list_comments():
    """List comments by project or task
    ---
    tags:
      - Comments
    parameters:
      - name: project_id
        in: query
        type: integer
      - name: task_id
        in: query
        type: integer
    """
    project_id = request.args.get('project_id', type=int)
    task_id = request.args.get('task_id', type=int)
    if not project_id and not task_id:
        return jsonify({'error': 'project_id or task_id is required'}), 400
    if project_id:
        comments = Comment.get_project_comments(project_id)
    else:
        comments = Comment.get_task_comments(task_id)
    return jsonify({'comments': [c.to_dict() for c in comments]})


@api_v1_bp.route('/comments', methods=['POST'])
@require_api_token('write:comments')
def create_comment():
    """Create comment
    ---
    tags:
      - Comments
    """
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    project_id = data.get('project_id')
    task_id = data.get('task_id')
    if not content:
        return jsonify({'error': 'content is required'}), 400
    if (not project_id and not task_id) or (project_id and task_id):
        return jsonify({'error': 'Provide either project_id or task_id'}), 400
    cmt = Comment(content=content, user_id=g.api_user.id, project_id=project_id, task_id=task_id, parent_id=data.get('parent_id'))
    db.session.add(cmt)
    db.session.commit()
    return jsonify({'message': 'Comment created successfully', 'comment': cmt.to_dict()}), 201


@api_v1_bp.route('/comments/<int:comment_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:comments')
def update_comment(comment_id):
    """Update comment
    ---
    tags:
      - Comments
    """
    cmt = Comment.query.get_or_404(comment_id)
    if cmt.user_id != g.api_user.id and not g.api_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    new_content = (data.get('content') or '').strip()
    if not new_content:
        return jsonify({'error': 'content is required'}), 400
    try:
        cmt.edit_content(new_content, g.api_user)
    except PermissionError:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'message': 'Comment updated successfully', 'comment': cmt.to_dict()})


@api_v1_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@require_api_token('write:comments')
def delete_comment(comment_id):
    """Delete comment
    ---
    tags:
      - Comments
    """
    cmt = Comment.query.get_or_404(comment_id)
    try:
        cmt.delete_comment(g.api_user)
    except PermissionError:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'message': 'Comment deleted successfully'})


# ==================== Client Notes ====================

@api_v1_bp.route('/clients/<int:client_id>/notes', methods=['GET'])
@require_api_token('read:clients')
def list_client_notes(client_id):
    """List client notes (paginated, important first)"""
    query = ClientNote.query.filter(ClientNote.client_id == client_id).order_by(
        ClientNote.is_important.desc(), ClientNote.created_at.desc()
    )
    result = paginate_query(query)
    return jsonify({'notes': [n.to_dict() for n in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/clients/<int:client_id>/notes', methods=['POST'])
@require_api_token('write:clients')
def create_client_note(client_id):
    """Create client note"""
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'content is required'}), 400
    note = ClientNote(content=content, user_id=g.api_user.id, client_id=client_id, is_important=bool(data.get('is_important', False)))
    db.session.add(note)
    db.session.commit()
    return jsonify({'message': 'Client note created successfully', 'note': note.to_dict()}), 201


@api_v1_bp.route('/client-notes/<int:note_id>', methods=['GET'])
@require_api_token('read:clients')
def get_client_note(note_id):
    note = ClientNote.query.get_or_404(note_id)
    return jsonify({'note': note.to_dict()})


@api_v1_bp.route('/client-notes/<int:note_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:clients')
def update_client_note(note_id):
    note = ClientNote.query.get_or_404(note_id)
    data = request.get_json() or {}
    new_content = (data.get('content') or '').strip()
    if not new_content:
        return jsonify({'error': 'content is required'}), 400
    if not (g.api_user.is_admin or note.user_id == g.api_user.id):
        return jsonify({'error': 'Access denied'}), 403
    note.content = new_content
    if 'is_important' in data:
        note.is_important = bool(data['is_important'])
    db.session.commit()
    return jsonify({'message': 'Client note updated successfully', 'note': note.to_dict()})


@api_v1_bp.route('/client-notes/<int:note_id>', methods=['DELETE'])
@require_api_token('write:clients')
def delete_client_note(note_id):
    note = ClientNote.query.get_or_404(note_id)
    if not (g.api_user.is_admin or note.user_id == g.api_user.id):
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Client note deleted successfully'})


# ==================== Project Costs ====================

@api_v1_bp.route('/projects/<int:project_id>/costs', methods=['GET'])
@require_api_token('read:projects')
def list_project_costs(project_id):
    """List project costs (paginated)"""
    start_date = _parse_date(request.args.get('start_date'))
    end_date = _parse_date(request.args.get('end_date'))
    user_id = request.args.get('user_id', type=int)
    billable_only = (request.args.get('billable_only', 'false').lower() == 'true')
    query = ProjectCost.query.filter(ProjectCost.project_id == project_id)
    if start_date:
        query = query.filter(ProjectCost.cost_date >= start_date)
    if end_date:
        query = query.filter(ProjectCost.cost_date <= end_date)
    if user_id:
        query = query.filter(ProjectCost.user_id == user_id)
    if billable_only:
        query = query.filter(ProjectCost.billable == True)
    query = query.order_by(ProjectCost.cost_date.desc(), ProjectCost.created_at.desc())
    result = paginate_query(query)
    return jsonify({'costs': [c.to_dict() for c in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/projects/<int:project_id>/costs', methods=['POST'])
@require_api_token('write:projects')
def create_project_cost(project_id):
    """Create project cost"""
    data = request.get_json() or {}
    required = ['description', 'category', 'amount', 'cost_date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    from decimal import Decimal
    try:
        amount = Decimal(str(data['amount']))
    except Exception:
        return jsonify({'error': 'Invalid amount'}), 400
    cost_date = _parse_date(data.get('cost_date'))
    if not cost_date:
        return jsonify({'error': 'Invalid cost_date'}), 400
    cost = ProjectCost(
        project_id=project_id,
        user_id=g.api_user.id,
        description=data['description'],
        category=data['category'],
        amount=amount,
        cost_date=cost_date,
        billable=bool(data.get('billable', True)),
        notes=data.get('notes'),
        currency_code=data.get('currency_code', 'EUR'),
    )
    db.session.add(cost)
    db.session.commit()
    return jsonify({'message': 'Project cost created successfully', 'cost': cost.to_dict()}), 201


@api_v1_bp.route('/project-costs/<int:cost_id>', methods=['GET'])
@require_api_token('read:projects')
def get_project_cost(cost_id):
    cost = ProjectCost.query.get_or_404(cost_id)
    return jsonify({'cost': cost.to_dict()})


@api_v1_bp.route('/project-costs/<int:cost_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:projects')
def update_project_cost(cost_id):
    cost = ProjectCost.query.get_or_404(cost_id)
    data = request.get_json() or {}
    for field in ('description', 'category', 'currency_code', 'notes', 'billable'):
        if field in data:
            setattr(cost, field, data[field])
    if 'amount' in data:
        try:
            from decimal import Decimal
            cost.amount = Decimal(str(data['amount']))
        except Exception:
            pass
    if 'cost_date' in data:
        parsed = _parse_date(data['cost_date'])
        if parsed:
            cost.cost_date = parsed
    db.session.commit()
    return jsonify({'message': 'Project cost updated successfully', 'cost': cost.to_dict()})


@api_v1_bp.route('/project-costs/<int:cost_id>', methods=['DELETE'])
@require_api_token('write:projects')
def delete_project_cost(cost_id):
    cost = ProjectCost.query.get_or_404(cost_id)
    db.session.delete(cost)
    db.session.commit()
    return jsonify({'message': 'Project cost deleted successfully'})


# ==================== Tax Rules (Admin) ====================

@api_v1_bp.route('/tax-rules', methods=['GET'])
@require_api_token('admin:all')
def list_tax_rules():
    """List tax rules (admin)"""
    rules = TaxRule.query.order_by(TaxRule.created_at.desc()).all()
    return jsonify({'tax_rules': [{
        'id': r.id,
        'name': r.name,
        'country': r.country,
        'region': r.region,
        'client_id': r.client_id,
        'project_id': r.project_id,
        'tax_code': r.tax_code,
        'rate_percent': float(r.rate_percent),
        'compound': r.compound,
        'inclusive': r.inclusive,
        'start_date': r.start_date.isoformat() if r.start_date else None,
        'end_date': r.end_date.isoformat() if r.end_date else None,
        'active': r.active,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in rules]})


@api_v1_bp.route('/tax-rules', methods=['POST'])
@require_api_token('admin:all')
def create_tax_rule():
    data = request.get_json() or {}
    required = ['name', 'rate_percent']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    from decimal import Decimal
    try:
        rate = Decimal(str(data['rate_percent']))
    except Exception:
        return jsonify({'error': 'Invalid rate_percent'}), 400
    rule = TaxRule(
        name=data['name'],
        country=data.get('country'),
        region=data.get('region'),
        client_id=data.get('client_id'),
        project_id=data.get('project_id'),
        tax_code=data.get('tax_code'),
        rate_percent=rate,
        compound=bool(data.get('compound', False)),
        inclusive=bool(data.get('inclusive', False)),
        start_date=_parse_date(data.get('start_date')),
        end_date=_parse_date(data.get('end_date')),
        active=bool(data.get('active', True)),
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({'message': 'Tax rule created successfully', 'tax_rule': {'id': rule.id}}), 201


@api_v1_bp.route('/tax-rules/<int:rule_id>', methods=['PUT', 'PATCH'])
@require_api_token('admin:all')
def update_tax_rule(rule_id):
    rule = TaxRule.query.get_or_404(rule_id)
    data = request.get_json() or {}
    for field in ('name', 'country', 'region', 'client_id', 'project_id', 'tax_code', 'compound', 'inclusive', 'active'):
        if field in data:
            setattr(rule, field, data[field])
    if 'rate_percent' in data:
        try:
            from decimal import Decimal
            rule.rate_percent = Decimal(str(data['rate_percent']))
        except Exception:
            pass
    if 'start_date' in data:
        rule.start_date = _parse_date(data['start_date'])
    if 'end_date' in data:
        rule.end_date = _parse_date(data['end_date'])
    db.session.commit()
    return jsonify({'message': 'Tax rule updated successfully'})


@api_v1_bp.route('/tax-rules/<int:rule_id>', methods=['DELETE'])
@require_api_token('admin:all')
def delete_tax_rule(rule_id):
    rule = TaxRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({'message': 'Tax rule deleted successfully'})


# ==================== Currencies & Exchange Rates ====================

@api_v1_bp.route('/currencies', methods=['GET'])
@require_api_token('read:invoices')
def list_currencies():
    cur_list = Currency.query.order_by(Currency.code.asc()).all()
    return jsonify({'currencies': [{
        'code': c.code, 'name': c.name, 'symbol': c.symbol, 'decimal_places': c.decimal_places, 'is_active': c.is_active
    } for c in cur_list]})


@api_v1_bp.route('/currencies', methods=['POST'])
@require_api_token('admin:all')
def create_currency():
    data = request.get_json() or {}
    required = ['code', 'name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    code = data['code'].upper().strip()
    if Currency.query.get(code):
        return jsonify({'error': 'Currency already exists'}), 400
    cur = Currency(code=code, name=data['name'], symbol=data.get('symbol'), decimal_places=int(data.get('decimal_places', 2)), is_active=bool(data.get('is_active', True)))
    db.session.add(cur)
    db.session.commit()
    return jsonify({'message': 'Currency created successfully', 'currency': {'code': cur.code}}), 201


@api_v1_bp.route('/currencies/<string:code>', methods=['PUT', 'PATCH'])
@require_api_token('admin:all')
def update_currency(code):
    cur = Currency.query.get_or_404(code.upper())
    data = request.get_json() or {}
    for field in ('name', 'symbol', 'decimal_places', 'is_active'):
        if field in data:
            setattr(cur, field, data[field])
    db.session.commit()
    return jsonify({'message': 'Currency updated successfully'})


@api_v1_bp.route('/exchange-rates', methods=['GET'])
@require_api_token('read:invoices')
def list_exchange_rates():
    base = request.args.get('base_code')
    quote = request.args.get('quote_code')
    date_str = request.args.get('date')
    q = ExchangeRate.query
    if base:
        q = q.filter(ExchangeRate.base_code == base.upper())
    if quote:
        q = q.filter(ExchangeRate.quote_code == quote.upper())
    if date_str:
        d = _parse_date(date_str)
        if d:
            q = q.filter(ExchangeRate.date == d)
    rates = q.order_by(ExchangeRate.date.desc()).limit(200).all()
    return jsonify({'exchange_rates': [{
        'id': r.id, 'base_code': r.base_code, 'quote_code': r.quote_code, 'rate': float(r.rate), 'date': r.date.isoformat(), 'source': r.source
    } for r in rates]})


@api_v1_bp.route('/exchange-rates', methods=['POST'])
@require_api_token('admin:all')
def create_exchange_rate():
    data = request.get_json() or {}
    required = ['base_code', 'quote_code', 'rate', 'date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    from decimal import Decimal
    try:
        rate_val = Decimal(str(data['rate']))
    except Exception:
        return jsonify({'error': 'Invalid rate'}), 400
    d = _parse_date(data['date'])
    if not d:
        return jsonify({'error': 'Invalid date'}), 400
    er = ExchangeRate(
        base_code=data['base_code'].upper(),
        quote_code=data['quote_code'].upper(),
        rate=rate_val,
        date=d,
        source=data.get('source'),
    )
    db.session.add(er)
    db.session.commit()
    return jsonify({'message': 'Exchange rate created successfully', 'exchange_rate': {'id': er.id}}), 201


@api_v1_bp.route('/exchange-rates/<int:rate_id>', methods=['PUT', 'PATCH'])
@require_api_token('admin:all')
def update_exchange_rate(rate_id):
    er = ExchangeRate.query.get_or_404(rate_id)
    data = request.get_json() or {}
    if 'rate' in data:
        try:
            from decimal import Decimal
            er.rate = Decimal(str(data['rate']))
        except Exception:
            pass
    if 'date' in data:
        d = _parse_date(data['date'])
        if d:
            er.date = d
    if 'source' in data:
        er.source = data['source']
    db.session.commit()
    return jsonify({'message': 'Exchange rate updated successfully'})


# ==================== Favorites ====================

@api_v1_bp.route('/users/me/favorites/projects', methods=['GET'])
@require_api_token('read:projects')
def list_favorite_projects():
    favs = UserFavoriteProject.query.filter_by(user_id=g.api_user.id).all()
    return jsonify({'favorites': [f.to_dict() for f in favs]})


@api_v1_bp.route('/users/me/favorites/projects', methods=['POST'])
@require_api_token('write:projects')
def add_favorite_project():
    data = request.get_json() or {}
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'error': 'project_id is required'}), 400
    # Prevent duplicates due to unique constraint
    existing = UserFavoriteProject.query.filter_by(user_id=g.api_user.id, project_id=project_id).first()
    if existing:
        return jsonify({'message': 'Already favorited', 'favorite': existing.to_dict()}), 200
    fav = UserFavoriteProject(user_id=g.api_user.id, project_id=project_id)
    db.session.add(fav)
    db.session.commit()
    return jsonify({'message': 'Project favorited successfully', 'favorite': fav.to_dict()}), 201


@api_v1_bp.route('/users/me/favorites/projects/<int:project_id>', methods=['DELETE'])
@require_api_token('write:projects')
def remove_favorite_project(project_id):
    fav = UserFavoriteProject.query.filter_by(user_id=g.api_user.id, project_id=project_id).first_or_404()
    db.session.delete(fav)
    db.session.commit()
    return jsonify({'message': 'Favorite removed successfully'})


# ==================== Audit Logs (Admin) ====================

@api_v1_bp.route('/audit-logs', methods=['GET'])
@require_api_token('admin:all')
def list_audit_logs():
    """List audit logs (admin)"""
    entity_type = request.args.get('entity_type')
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    limit = request.args.get('limit', type=int) or 100
    q = AuditLog.query
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({'audit_logs': [l.to_dict() for l in logs]})


# ==================== Activities ====================

@api_v1_bp.route('/activities', methods=['GET'])
@require_api_token('read:reports')
def list_activities():
    """List activities"""
    user_id = request.args.get('user_id', type=int)
    entity_type = request.args.get('entity_type')
    limit = request.args.get('limit', type=int) or 50
    acts = Activity.get_recent(user_id=user_id, limit=limit, entity_type=entity_type)
    return jsonify({'activities': [a.to_dict() for a in acts]})


# ==================== Invoice PDF Templates (Admin) ====================

@api_v1_bp.route('/invoice-pdf-templates', methods=['GET'])
@require_api_token('admin:all')
def list_invoice_pdf_templates():
    templates = InvoicePDFTemplate.get_all_templates()
    return jsonify({'templates': [t.to_dict() for t in templates]})


@api_v1_bp.route('/invoice-pdf-templates/<string:page_size>', methods=['GET'])
@require_api_token('admin:all')
def get_invoice_pdf_template(page_size):
    tpl = InvoicePDFTemplate.get_template(page_size)
    return jsonify({'template': tpl.to_dict()})


# ==================== Invoice Templates (Admin) ====================

@api_v1_bp.route('/invoice-templates', methods=['GET'])
@require_api_token('admin:all')
def list_invoice_templates():
    """List invoice templates (admin)"""
    templates = InvoiceTemplate.query.order_by(InvoiceTemplate.name.asc()).all()
    return jsonify({'templates': [{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'html': t.html or '',
        'css': t.css or '',
        'is_default': t.is_default,
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None,
    } for t in templates]})


@api_v1_bp.route('/invoice-templates/<int:template_id>', methods=['GET'])
@require_api_token('admin:all')
def get_invoice_template(template_id):
    t = InvoiceTemplate.query.get_or_404(template_id)
    return jsonify({'template': {
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'html': t.html or '',
        'css': t.css or '',
        'is_default': t.is_default,
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None,
    }})


@api_v1_bp.route('/invoice-templates', methods=['POST'])
@require_api_token('admin:all')
def create_invoice_template():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    # Enforce unique name
    if InvoiceTemplate.query.filter_by(name=name).first():
        return jsonify({'error': 'Template name already exists'}), 400
    is_default = bool(data.get('is_default', False))
    if is_default:
        InvoiceTemplate.query.update({InvoiceTemplate.is_default: False})
    t = InvoiceTemplate(
        name=name,
        description=(data.get('description') or '').strip() or None,
        html=(data.get('html') or '').strip() or None,
        css=(data.get('css') or '').strip() or None,
        is_default=is_default,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({'message': 'Invoice template created successfully', 'template': {'id': t.id}}), 201


@api_v1_bp.route('/invoice-templates/<int:template_id>', methods=['PUT', 'PATCH'])
@require_api_token('admin:all')
def update_invoice_template(template_id):
    t = InvoiceTemplate.query.get_or_404(template_id)
    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name cannot be empty'}), 400
        # Check duplicate name
        existing = InvoiceTemplate.query.filter(InvoiceTemplate.name == name, InvoiceTemplate.id != template_id).first()
        if existing:
            return jsonify({'error': 'Template name already exists'}), 400
        t.name = name
    for field in ('description', 'html', 'css'):
        if field in data:
            setattr(t, field, (data.get(field) or '').strip() or None)
    if 'is_default' in data and bool(data['is_default']):
        # set this as default, unset others
        InvoiceTemplate.query.filter(InvoiceTemplate.id != template_id).update({InvoiceTemplate.is_default: False})
        t.is_default = True
    db.session.commit()
    return jsonify({'message': 'Invoice template updated successfully'})


@api_v1_bp.route('/invoice-templates/<int:template_id>', methods=['DELETE'])
@require_api_token('admin:all')
def delete_invoice_template(template_id):
    t = InvoiceTemplate.query.get_or_404(template_id)
    # In a stricter implementation, we could prevent deletion if referenced
    db.session.delete(t)
    db.session.commit()
    return jsonify({'message': 'Invoice template deleted successfully'})

# ==================== Recurring Invoices ====================

@api_v1_bp.route('/recurring-invoices', methods=['GET'])
@require_api_token('read:recurring_invoices')
def list_recurring_invoices():
    """List recurring invoice templates
    ---
    tags:
      - RecurringInvoices
    """
    query = RecurringInvoice.query
    is_active = request.args.get('is_active')
    if is_active is not None:
        query = query.filter(RecurringInvoice.is_active == (is_active.lower() == 'true'))
    client_id = request.args.get('client_id', type=int)
    if client_id:
        query = query.filter(RecurringInvoice.client_id == client_id)
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter(RecurringInvoice.project_id == project_id)
    result = paginate_query(query.order_by(RecurringInvoice.created_at.desc()))
    return jsonify({'recurring_invoices': [ri.to_dict() for ri in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/recurring-invoices/<int:ri_id>', methods=['GET'])
@require_api_token('read:recurring_invoices')
def get_recurring_invoice(ri_id):
    """Get a recurring invoice template"""
    ri = RecurringInvoice.query.get_or_404(ri_id)
    return jsonify({'recurring_invoice': ri.to_dict()})


@api_v1_bp.route('/recurring-invoices', methods=['POST'])
@require_api_token('write:recurring_invoices')
def create_recurring_invoice():
    """Create a recurring invoice template
    ---
    tags:
      - RecurringInvoices
    """
    data = request.get_json() or {}
    required = ['name', 'project_id', 'client_id', 'client_name', 'frequency', 'next_run_date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    freq = (data.get('frequency') or '').lower()
    if freq not in ('daily', 'weekly', 'monthly', 'yearly'):
        return jsonify({'error': 'Invalid frequency'}), 400
    next_date = _parse_date(data.get('next_run_date'))
    if not next_date:
        return jsonify({'error': 'Invalid next_run_date (YYYY-MM-DD)'}), 400
    ri = RecurringInvoice(
        name=data['name'],
        project_id=data['project_id'],
        client_id=data['client_id'],
        frequency=freq,
        next_run_date=next_date,
        created_by=g.api_user.id,
        interval=data.get('interval', 1),
        end_date=_parse_date(data.get('end_date')),
        client_name=data['client_name'],
        client_email=data.get('client_email'),
        client_address=data.get('client_address'),
        due_date_days=data.get('due_date_days', 30),
        tax_rate=data.get('tax_rate', 0),
        currency_code=data.get('currency_code', 'EUR'),
        notes=data.get('notes'),
        terms=data.get('terms'),
        template_id=data.get('template_id'),
        auto_send=bool(data.get('auto_send', False)),
        auto_include_time_entries=bool(data.get('auto_include_time_entries', True)),
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(ri)
    db.session.commit()
    return jsonify({'message': 'Recurring invoice created successfully', 'recurring_invoice': ri.to_dict()}), 201


@api_v1_bp.route('/recurring-invoices/<int:ri_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:recurring_invoices')
def update_recurring_invoice(ri_id):
    """Update a recurring invoice template"""
    ri = RecurringInvoice.query.get_or_404(ri_id)
    data = request.get_json() or {}
    for field in ('name', 'client_name', 'client_email', 'client_address', 'notes', 'terms', 'currency_code'):
        if field in data:
            setattr(ri, field, data[field])
    if 'frequency' in data and data['frequency'] in ('daily', 'weekly', 'monthly', 'yearly'):
        ri.frequency = data['frequency']
    if 'interval' in data:
        try:
            ri.interval = int(data['interval'])
        except Exception:
            pass
    if 'next_run_date' in data:
        parsed = _parse_date(data['next_run_date'])
        if parsed:
            ri.next_run_date = parsed
    if 'end_date' in data:
        ri.end_date = _parse_date(data['end_date'])
    for bfield in ('auto_send', 'auto_include_time_entries', 'is_active'):
        if bfield in data:
            setattr(ri, bfield, bool(data[bfield]))
    if 'due_date_days' in data:
        try:
            ri.due_date_days = int(data['due_date_days'])
        except Exception:
            pass
    if 'tax_rate' in data:
        try:
            from decimal import Decimal
            ri.tax_rate = Decimal(str(data['tax_rate']))
        except Exception:
            pass
    db.session.commit()
    return jsonify({'message': 'Recurring invoice updated successfully', 'recurring_invoice': ri.to_dict()})


@api_v1_bp.route('/recurring-invoices/<int:ri_id>', methods=['DELETE'])
@require_api_token('write:recurring_invoices')
def delete_recurring_invoice(ri_id):
    """Deactivate a recurring invoice template"""
    ri = RecurringInvoice.query.get_or_404(ri_id)
    ri.is_active = False
    db.session.commit()
    return jsonify({'message': 'Recurring invoice deactivated successfully'})


@api_v1_bp.route('/recurring-invoices/<int:ri_id>/generate', methods=['POST'])
@require_api_token('write:recurring_invoices')
def generate_from_recurring_invoice(ri_id):
    """Generate an invoice from a recurring template"""
    ri = RecurringInvoice.query.get_or_404(ri_id)
    invoice = ri.generate_invoice()
    if not invoice:
        return jsonify({'message': 'No invoice generated (not due yet or inactive)'}), 200
    db.session.commit()
    return jsonify({'message': 'Invoice generated successfully', 'invoice': invoice.to_dict()}), 201


# ==================== Credit Notes ====================

@api_v1_bp.route('/credit-notes', methods=['GET'])
@require_api_token('read:invoices')
def list_credit_notes():
    """List credit notes
    ---
    tags:
      - CreditNotes
    """
    query = CreditNote.query
    invoice_id = request.args.get('invoice_id', type=int)
    if invoice_id:
        query = query.filter(CreditNote.invoice_id == invoice_id)
    result = paginate_query(query.order_by(CreditNote.created_at.desc()))
    return jsonify({'credit_notes': [{
        'id': cn.id,
        'invoice_id': cn.invoice_id,
        'credit_number': cn.credit_number,
        'amount': float(cn.amount),
        'reason': cn.reason,
        'created_by': cn.created_by,
        'created_at': cn.created_at.isoformat() if cn.created_at else None
    } for cn in result['items']], 'pagination': result['pagination']})


@api_v1_bp.route('/credit-notes/<int:cn_id>', methods=['GET'])
@require_api_token('read:invoices')
def get_credit_note(cn_id):
    """Get credit note"""
    cn = CreditNote.query.get_or_404(cn_id)
    return jsonify({'credit_note': {
        'id': cn.id,
        'invoice_id': cn.invoice_id,
        'credit_number': cn.credit_number,
        'amount': float(cn.amount),
        'reason': cn.reason,
        'created_by': cn.created_by,
        'created_at': cn.created_at.isoformat() if cn.created_at else None
    }})


@api_v1_bp.route('/credit-notes', methods=['POST'])
@require_api_token('write:invoices')
def create_credit_note():
    """Create credit note"""
    data = request.get_json() or {}
    required = ['invoice_id', 'amount']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing required fields: {', '.join(missing)}"}), 400
    inv = Invoice.query.get(data['invoice_id'])
    if not inv:
        return jsonify({'error': 'Invalid invoice_id'}), 400
    from decimal import Decimal
    try:
        amt = Decimal(str(data['amount']))
    except Exception:
        return jsonify({'error': 'Invalid amount'}), 400
    # Generate credit number (simple: CN-<invoice_id>-<timestamp>)
    credit_number = f"CN-{inv.id}-{int(datetime.utcnow().timestamp())}"
    cn = CreditNote(
        invoice_id=inv.id,
        credit_number=credit_number,
        amount=amt,
        reason=data.get('reason'),
        created_by=g.api_user.id,
    )
    db.session.add(cn)
    db.session.commit()
    return jsonify({'message': 'Credit note created successfully', 'credit_note': {
        'id': cn.id,
        'invoice_id': cn.invoice_id,
        'credit_number': cn.credit_number,
        'amount': float(cn.amount),
        'reason': cn.reason,
        'created_by': cn.created_by,
        'created_at': cn.created_at.isoformat() if cn.created_at else None
    }}), 201


@api_v1_bp.route('/credit-notes/<int:cn_id>', methods=['PUT', 'PATCH'])
@require_api_token('write:invoices')
def update_credit_note(cn_id):
    """Update credit note"""
    cn = CreditNote.query.get_or_404(cn_id)
    data = request.get_json() or {}
    if 'reason' in data:
        cn.reason = data['reason']
    if 'amount' in data:
        try:
            from decimal import Decimal
            cn.amount = Decimal(str(data['amount']))
        except Exception:
            pass
    db.session.commit()
    return jsonify({'message': 'Credit note updated successfully'})


@api_v1_bp.route('/credit-notes/<int:cn_id>', methods=['DELETE'])
@require_api_token('write:invoices')
def delete_credit_note(cn_id):
    """Delete credit note"""
    cn = CreditNote.query.get_or_404(cn_id)
    db.session.delete(cn)
    db.session.commit()
    return jsonify({'message': 'Credit note deleted successfully'})

# ==================== Reports ====================

@api_v1_bp.route('/reports/summary', methods=['GET'])
@require_api_token('read:reports')
def report_summary():
    """Get time tracking summary report
    ---
    tags:
      - Reports
    parameters:
      - name: start_date
        in: query
        type: string
        format: date
      - name: end_date
        in: query
        type: string
        format: date
      - name: project_id
        in: query
        type: integer
      - name: user_id
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: Summary report
    """
    # Date range (default to last 30 days)
    end_date = request.args.get('end_date')
    start_date = request.args.get('start_date')
    
    if not end_date:
        end_dt = datetime.utcnow()
    else:
        end_dt = parse_datetime(end_date) or datetime.utcnow()
    
    if not start_date:
        start_dt = end_dt - timedelta(days=30)
    else:
        start_dt = parse_datetime(start_date) or (end_dt - timedelta(days=30))
    
    # Build query
    query = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None),
        TimeEntry.start_time >= start_dt,
        TimeEntry.start_time <= end_dt
    )
    
    # Filter by user
    user_id = request.args.get('user_id', type=int)
    if user_id:
        if g.api_user.is_admin or user_id == g.api_user.id:
            query = query.filter_by(user_id=user_id)
        else:
            return jsonify({'error': 'Access denied'}), 403
    elif not g.api_user.is_admin:
        query = query.filter_by(user_id=g.api_user.id)
    
    # Filter by project
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    entries = query.all()
    
    # Calculate summary
    total_hours = sum(e.duration_hours or 0 for e in entries)
    billable_hours = sum(e.duration_hours or 0 for e in entries if e.billable)
    total_entries = len(entries)
    
    # Group by project
    by_project = {}
    for entry in entries:
        if entry.project_id:
            if entry.project_id not in by_project:
                by_project[entry.project_id] = {
                    'project_id': entry.project_id,
                    'project_name': entry.project.name if entry.project else 'Unknown',
                    'hours': 0,
                    'entries': 0
                }
            by_project[entry.project_id]['hours'] += entry.duration_hours or 0
            by_project[entry.project_id]['entries'] += 1
    
    return jsonify({
        'summary': {
            'start_date': start_dt.isoformat(),
            'end_date': end_dt.isoformat(),
            'total_hours': round(total_hours, 2),
            'billable_hours': round(billable_hours, 2),
            'total_entries': total_entries,
            'by_project': list(by_project.values())
        }
    })


# ==================== Users ====================

@api_v1_bp.route('/users/me', methods=['GET'])
@require_api_token('read:users')
def get_current_user():
    """Get current authenticated user information
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Current user information
    """
    return jsonify({'user': g.api_user.to_dict()})


@api_v1_bp.route('/users', methods=['GET'])
@require_api_token('admin:all')
def list_users():
    """List all users (admin only)
    ---
    tags:
      - Users
    parameters:
      - name: page
        in: query
        type: integer
      - name: per_page
        in: query
        type: integer
    security:
      - Bearer: []
    responses:
      200:
        description: List of users
    """
    query = User.query.filter_by(is_active=True).order_by(User.username)
    
    # Paginate
    result = paginate_query(query)
    
    return jsonify({
        'users': [u.to_dict() for u in result['items']],
        'pagination': result['pagination']
    })


# ==================== Error Handlers ====================

@api_v1_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404


@api_v1_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

