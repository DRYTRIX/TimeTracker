from flask import Blueprint, request, redirect, url_for, flash, jsonify, render_template
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Comment, Project, Task, Quote
from app.utils.db import safe_commit

comments_bp = Blueprint('comments', __name__)

@comments_bp.route('/comments/create', methods=['POST'])
@login_required
def create_comment():
    """Create a new comment for a project or task"""
    try:
        content = request.form.get('content', '').strip()
        project_id = request.form.get('project_id', type=int)
        task_id = request.form.get('task_id', type=int)
        quote_id = request.form.get('quote_id', type=int)
        parent_id = request.form.get('parent_id', type=int)
        is_internal = request.form.get('is_internal', 'true').lower() == 'true'
        
        # Validation
        if not content:
            flash(_('Comment content cannot be empty'), 'error')
            return redirect(request.referrer or url_for('main.dashboard'))
        
        if not project_id and not task_id and not quote_id:
            flash(_('Comment must be associated with a project, task, or quote'), 'error')
            return redirect(request.referrer or url_for('main.dashboard'))
        
        # Ensure only one target is set
        targets = [x for x in [project_id, task_id, quote_id] if x is not None]
        if len(targets) > 1:
            flash(_('Comment cannot be associated with multiple targets'), 'error')
            return redirect(request.referrer or url_for('main.dashboard'))
        
        # Verify target exists
        if project_id:
            target = Project.query.get_or_404(project_id)
            target_type = 'project'
        elif task_id:
            target = Task.query.get_or_404(task_id)
            target_type = 'task'
            project_id = target.project_id  # For redirects
        else:
            target = Quote.query.get_or_404(quote_id)
            target_type = 'quote'
        
        # If this is a reply, verify parent comment exists
        if parent_id:
            parent_comment = Comment.query.get_or_404(parent_id)
            # Verify parent is for the same target
            if (project_id and parent_comment.project_id != project_id) or \
               (task_id and parent_comment.task_id != task_id) or \
               (quote_id and parent_comment.quote_id != quote_id):
                flash(_('Invalid parent comment'), 'error')
                return redirect(request.referrer or url_for('main.dashboard'))
        
        # Create the comment
        comment = Comment(
            content=content,
            user_id=current_user.id,
            project_id=project_id if target_type == 'project' else None,
            task_id=task_id if target_type == 'task' else None,
            quote_id=quote_id if target_type == 'quote' else None,
            parent_id=parent_id,
            is_internal=is_internal
        )
        
        db.session.add(comment)
        if safe_commit():
            # Log comment creation
            log_event("comment.created", 
                     user_id=current_user.id, 
                     comment_id=comment.id,
                     target_type=target_type)
            track_event(current_user.id, "comment.created", {
                "comment_id": comment.id,
                "target_type": target_type
            })
            flash(_('Comment added successfully'), 'success')
        else:
            flash(_('Error adding comment'), 'error')
    
    except Exception as e:
        flash(_('Error adding comment: %(error)s', error=str(e)), 'error')
    
    # Redirect back to the source page
    if project_id:
        return redirect(url_for('projects.view_project', project_id=project_id))
    elif task_id:
        return redirect(url_for('tasks.view_task', task_id=task_id))
    elif quote_id:
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    else:
        return redirect(request.referrer or url_for('main.dashboard'))

@comments_bp.route('/comments/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    """Edit an existing comment"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Check permissions
    if not comment.can_edit(current_user):
        flash(_('You do not have permission to edit this comment'), 'error')
        return redirect(request.referrer or url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            content = request.form.get('content', '').strip()
            
            if not content:
                flash(_('Comment content cannot be empty'), 'error')
                return render_template('comments/edit.html', comment=comment)
            
            comment.edit_content(content, current_user)
            
            # Log comment update
            log_event("comment.updated", user_id=current_user.id, comment_id=comment.id)
            track_event(current_user.id, "comment.updated", {"comment_id": comment.id})
            
            flash(_('Comment updated successfully'), 'success')
            
            # Redirect back to the source page
            if comment.project_id:
                return redirect(url_for('projects.view_project', project_id=comment.project_id))
            elif comment.task_id:
                return redirect(url_for('tasks.view_task', task_id=comment.task_id))
            elif comment.quote_id:
                return redirect(url_for('quotes.view_quote', quote_id=comment.quote_id))
            else:
                return redirect(url_for('main.dashboard'))
        
        except Exception as e:
            flash(_('Error updating comment: %(error)s', error=str(e)), 'error')
    
    return render_template('comments/edit.html', comment=comment)

@comments_bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Check permissions
    if not comment.can_delete(current_user):
        flash(_('You do not have permission to delete this comment'), 'error')
        return redirect(request.referrer or url_for('main.dashboard'))
    
    try:
        project_id = comment.project_id
        task_id = comment.task_id
        quote_id = comment.quote_id
        comment_id_for_log = comment.id
        
        comment.delete_comment(current_user)
        
        # Log comment deletion
        log_event("comment.deleted", user_id=current_user.id, comment_id=comment_id_for_log)
        track_event(current_user.id, "comment.deleted", {"comment_id": comment_id_for_log})
        
        flash(_('Comment deleted successfully'), 'success')
        
        # Redirect back to the source page
        if project_id:
            return redirect(url_for('projects.view_project', project_id=project_id))
        elif task_id:
            return redirect(url_for('tasks.view_task', task_id=task_id))
        elif quote_id:
            return redirect(url_for('quotes.view_quote', quote_id=quote_id))
        else:
            return redirect(url_for('main.dashboard'))
    
    except Exception as e:
        flash(_('Error deleting comment: %(error)s', error=str(e)), 'error')
        return redirect(request.referrer or url_for('main.dashboard'))

@comments_bp.route('/api/comments')
@login_required
def list_comments():
    """API endpoint to get comments for a project, task, or quote"""
    project_id = request.args.get('project_id', type=int)
    task_id = request.args.get('task_id', type=int)
    quote_id = request.args.get('quote_id', type=int)
    include_replies = request.args.get('include_replies', 'true').lower() == 'true'
    include_internal = request.args.get('include_internal', 'true').lower() == 'true'
    
    targets = [x for x in [project_id, task_id, quote_id] if x is not None]
    if len(targets) == 0:
        return jsonify({'error': 'project_id, task_id, or quote_id is required'}), 400
    
    if len(targets) > 1:
        return jsonify({'error': 'Cannot specify multiple targets'}), 400
    
    try:
        if project_id:
            # Verify project exists
            project = Project.query.get_or_404(project_id)
            comments = Comment.get_project_comments(project_id, include_replies)
        elif task_id:
            # Verify task exists
            task = Task.query.get_or_404(task_id)
            comments = Comment.get_task_comments(task_id, include_replies)
        else:
            # Verify quote exists
            quote = Quote.query.get_or_404(quote_id)
            comments = Comment.get_quote_comments(quote_id, include_replies, include_internal)
        
        return jsonify({
            'success': True,
            'comments': [comment.to_dict() for comment in comments]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@comments_bp.route('/api/comments/<int:comment_id>')
@login_required
def get_comment(comment_id):
    """API endpoint to get a single comment"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        return jsonify({
            'success': True,
            'comment': comment.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@comments_bp.route('/api/comments/recent')
@login_required
def get_recent_comments():
    """API endpoint to get recent comments"""
    limit = request.args.get('limit', 10, type=int)
    
    try:
        comments = Comment.get_recent_comments(limit)
        return jsonify({
            'success': True,
            'comments': [comment.to_dict() for comment in comments]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@comments_bp.route('/api/comments/user/<int:user_id>')
@login_required
def get_user_comments(user_id):
    """API endpoint to get comments by a specific user"""
    limit = request.args.get('limit', type=int)
    
    # Only allow users to see their own comments unless they're admin
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        comments = Comment.get_user_comments(user_id, limit)
        return jsonify({
            'success': True,
            'comments': [comment.to_dict() for comment in comments]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
