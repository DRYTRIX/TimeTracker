"""REST API v1 - Comprehensive API endpoints with token authentication"""
from flask import Blueprint, jsonify, request, current_app, g
from app import db
from app.models import (
    User, Project, TimeEntry, Task, Client, Invoice, Expense,
    SavedFilter, FocusSession, RecurringBlock, Comment
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
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})


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

