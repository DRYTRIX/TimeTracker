"""
Workflow Engine Service
Handles workflow rule evaluation and execution
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app import db
from app.models.workflow import WorkflowRule, WorkflowExecution
from app.models import TimeEntry, Task, Project, User
import time
import logging

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Engine for evaluating and executing workflow rules"""

    @staticmethod
    def evaluate_trigger(rule: WorkflowRule, event: Dict[str, Any]) -> bool:
        """Check if a rule should be triggered by an event"""
        if not rule.enabled:
            return False

        if rule.trigger_type != event.get("type"):
            return False

        # Evaluate additional conditions if present
        if rule.trigger_conditions:
            if not WorkflowEngine._evaluate_conditions(rule.trigger_conditions, event.get("data", {})):
                return False

        return True

    @staticmethod
    def _evaluate_conditions(conditions: List[Dict], event_data: Dict) -> bool:
        """Evaluate trigger conditions against event data"""
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")

            if field not in event_data:
                return False

            event_value = event_data[field]

            if not WorkflowEngine._compare_values(event_value, operator, value):
                return False

        return True

    @staticmethod
    def _compare_values(actual: Any, operator: str, expected: Any) -> bool:
        """Compare values based on operator"""
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == ">":
            return actual > expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "<":
            return actual < expected
        elif operator == "<=":
            return actual <= expected
        elif operator == "in":
            return actual in expected if isinstance(expected, list) else False
        elif operator == "not_in":
            return actual not in expected if isinstance(expected, list) else True
        elif operator == "contains":
            return expected in str(actual) if actual else False
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    @staticmethod
    def execute_rule(rule: WorkflowRule, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow rule"""
        start_time = time.time()

        try:
            # Evaluate trigger
            if not WorkflowEngine.evaluate_trigger(rule, event):
                return {
                    "success": False,
                    "message": "Trigger conditions not met",
                    "executed": False,
                }

            # Execute actions
            results = []
            context = event.get("data", {})

            for action in rule.actions:
                try:
                    result = WorkflowEngine._perform_action(action, context, rule)
                    results.append({"action": action, "success": True, "result": result})
                except Exception as e:
                    logger.error(f"Error executing action {action}: {e}")
                    results.append({"action": action, "success": False, "error": str(e)})

            # Log execution
            execution_time_ms = int((time.time() - start_time) * 1000)
            success = all(r.get("success", False) for r in results)

            execution = WorkflowExecution(
                rule_id=rule.id,
                executed_at=datetime.utcnow(),
                success=success,
                error_message=None if success else "Some actions failed",
                result=results,
                trigger_event=event,
                execution_time_ms=execution_time_ms,
            )
            db.session.add(execution)

            # Update rule stats
            rule.last_executed_at = datetime.utcnow()
            rule.execution_count += 1

            db.session.commit()

            return {
                "success": success,
                "message": "Workflow executed successfully" if success else "Some actions failed",
                "results": results,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            logger.error(f"Error executing workflow rule {rule.id}: {e}")

            execution_time_ms = int((time.time() - start_time) * 1000)
            execution = WorkflowExecution(
                rule_id=rule.id,
                executed_at=datetime.utcnow(),
                success=False,
                error_message=str(e),
                result=None,
                trigger_event=event,
                execution_time_ms=execution_time_ms,
            )
            db.session.add(execution)
            db.session.commit()

            return {
                "success": False,
                "message": f"Workflow execution failed: {str(e)}",
                "error": str(e),
            }

    @staticmethod
    def _perform_action(action: Dict[str, Any], context: Dict[str, Any], rule: WorkflowRule) -> Any:
        """Perform a single action"""
        action_type = action.get("type")

        if action_type == "log_time":
            return WorkflowEngine._action_log_time(action, context)
        elif action_type == "send_notification":
            return WorkflowEngine._action_send_notification(action, context)
        elif action_type == "update_status":
            return WorkflowEngine._action_update_status(action, context)
        elif action_type == "assign_task":
            return WorkflowEngine._action_assign_task(action, context)
        elif action_type == "create_task":
            return WorkflowEngine._action_create_task(action, context)
        elif action_type == "update_project":
            return WorkflowEngine._action_update_project(action, context)
        elif action_type == "send_email":
            return WorkflowEngine._action_send_email(action, context)
        elif action_type == "webhook":
            return WorkflowEngine._action_webhook(action, context)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    @staticmethod
    def _action_log_time(action: Dict, context: Dict, rule: WorkflowRule) -> Dict:
        """Auto-log time entry"""
        from app.services.time_tracking_service import TimeTrackingService

        service = TimeTrackingService()

        # Resolve template variables
        project_id = WorkflowEngine._resolve_template(action.get("project_id"), context)
        task_id = WorkflowEngine._resolve_template(action.get("task_id"), context)
        duration = WorkflowEngine._resolve_template(action.get("duration"), context)
        notes = WorkflowEngine._resolve_template(action.get("notes", ""), context)

        if not project_id:
            raise ValueError("project_id is required for log_time action")

        # Calculate start/end time from duration
        from datetime import timedelta

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=float(duration) if duration else 0)

        result = service.create_manual_entry(
            user_id=context.get("user_id") or rule.user_id,
            project_id=int(project_id),
            start_time=start_time,
            end_time=end_time,
            task_id=int(task_id) if task_id else None,
            notes=notes,
            billable=action.get("billable", True),
        )

        return result

    @staticmethod
    def _action_send_notification(action: Dict, context: Dict) -> Dict:
        """Send notification"""
        from app.utils.notification_service import NotificationService

        service = NotificationService()

        title = WorkflowEngine._resolve_template(action.get("title", ""), context)
        message = WorkflowEngine._resolve_template(action.get("message", ""), context)
        user_id = WorkflowEngine._resolve_template(action.get("user_id"), context) or context.get("user_id")

        if not user_id:
            raise ValueError("user_id is required for send_notification action")

        service.send_notification(
            user_id=int(user_id),
            title=title,
            message=message,
            type=action.get("notification_type", "info"),
            priority=action.get("priority", "normal"),
        )

        return {"sent": True, "user_id": user_id}

    @staticmethod
    def _action_update_status(action: Dict, context: Dict) -> Dict:
        """Update task/project status"""
        entity_type = action.get("entity_type")  # 'task' or 'project'
        entity_id = WorkflowEngine._resolve_template(action.get("entity_id"), context)
        status = action.get("status")

        if entity_type == "task":
            task = Task.query.get(entity_id)
            if task:
                task.status = status
                db.session.commit()
                return {"updated": True, "entity": "task", "id": entity_id}
        elif entity_type == "project":
            project = Project.query.get(entity_id)
            if project:
                project.status = status
                db.session.commit()
                return {"updated": True, "entity": "project", "id": entity_id}

        raise ValueError(f"Entity not found: {entity_type} {entity_id}")

    @staticmethod
    def _action_assign_task(action: Dict, context: Dict) -> Dict:
        """Assign task to user"""
        task_id = WorkflowEngine._resolve_template(action.get("task_id"), context)
        user_id = WorkflowEngine._resolve_template(action.get("user_id"), context)

        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.assigned_to = int(user_id)
        db.session.commit()

        return {"assigned": True, "task_id": task_id, "user_id": user_id}

    @staticmethod
    def _action_create_task(action: Dict, context: Dict) -> Dict:
        """Create a new task"""
        project_id = WorkflowEngine._resolve_template(action.get("project_id"), context)
        name = WorkflowEngine._resolve_template(action.get("name"), context)
        description = WorkflowEngine._resolve_template(action.get("description", ""), context)

        if not project_id or not name:
            raise ValueError("project_id and name are required for create_task action")

        task = Task(
            project_id=int(project_id),
            name=name,
            description=description,
            status=action.get("status", "todo"),
            priority=action.get("priority", "medium"),
        )
        db.session.add(task)
        db.session.commit()

        return {"created": True, "task_id": task.id}

    @staticmethod
    def _action_update_project(action: Dict, context: Dict) -> Dict:
        """Update project"""
        project_id = WorkflowEngine._resolve_template(action.get("project_id"), context)
        updates = action.get("updates", {})

        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        for key, value in updates.items():
            if hasattr(project, key):
                resolved_value = WorkflowEngine._resolve_template(value, context)
                setattr(project, key, resolved_value)

        db.session.commit()

        return {"updated": True, "project_id": project_id}

    @staticmethod
    def _action_send_email(action: Dict, context: Dict) -> Dict:
        """Send email"""
        from app.utils.email import send_email

        to = WorkflowEngine._resolve_template(action.get("to"), context)
        subject = WorkflowEngine._resolve_template(action.get("subject"), context)
        template = action.get("template")
        data = action.get("data", {})

        # Resolve template variables in data
        resolved_data = {k: WorkflowEngine._resolve_template(v, context) for k, v in data.items()}

        send_email(to=to, subject=subject, template=template, **resolved_data)

        return {"sent": True, "to": to}

    @staticmethod
    def _action_webhook(action: Dict, context: Dict) -> Dict:
        """Trigger webhook"""
        import requests

        url = action.get("url")
        method = action.get("method", "POST")
        payload = action.get("payload", {})

        # Resolve template variables in payload
        resolved_payload = {k: WorkflowEngine._resolve_template(v, context) for k, v in payload.items()}

        response = requests.request(method=method, url=url, json=resolved_payload, timeout=10)

        return {"sent": True, "status_code": response.status_code}

    @staticmethod
    def _resolve_template(value: Any, context: Dict) -> Any:
        """Resolve template variables like {{task.name}}"""
        if isinstance(value, str):
            import re

            def replace_var(match):
                var_path = match.group(1).strip()
                parts = var_path.split(".")
                result = context
                for part in parts:
                    if isinstance(result, dict):
                        result = result.get(part)
                    elif hasattr(result, part):
                        result = getattr(result, part)
                    else:
                        return match.group(0)  # Return original if not found
                return str(result) if result is not None else ""

            return re.sub(r"\{\{([^}]+)\}\}", replace_var, value)
        return value

    @staticmethod
    def trigger_event(event_type: str, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Trigger workflow evaluation for an event"""
        # Get all enabled rules for this trigger type, ordered by priority
        rules = (
            WorkflowRule.query.filter(
                WorkflowRule.trigger_type == event_type, WorkflowRule.enabled == True
            )
            .order_by(WorkflowRule.priority.desc())
            .all()
        )

        event = {"type": event_type, "data": event_data}
        results = []

        for rule in rules:
            try:
                result = WorkflowEngine.execute_rule(rule, event)
                results.append({"rule_id": rule.id, "rule_name": rule.name, **result})
            except Exception as e:
                logger.error(f"Error executing rule {rule.id}: {e}")
                results.append({"rule_id": rule.id, "rule_name": rule.name, "success": False, "error": str(e)})

        return results

