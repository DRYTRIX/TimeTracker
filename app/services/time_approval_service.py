"""
Time Entry Approval Service
Handles approval workflow for time entries
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app import db
from app.models.time_entry_approval import TimeEntryApproval, ApprovalPolicy, ApprovalStatus
from app.models import TimeEntry, User
import logging

logger = logging.getLogger(__name__)


class TimeApprovalService:
    """Service for managing time entry approvals"""

    def request_approval(
        self, time_entry_id: int, requested_by: int, comment: str = None, approver_ids: List[int] = None
    ) -> Dict[str, Any]:
        """Request approval for a time entry"""
        time_entry = TimeEntry.query.get(time_entry_id)
        if not time_entry:
            return {"success": False, "message": "Time entry not found", "error": "not_found"}

        # Check if already pending
        existing = TimeEntryApproval.query.filter_by(time_entry_id=time_entry_id, status=ApprovalStatus.PENDING).first()

        if existing:
            return {"success": False, "message": "Approval already pending", "error": "already_pending"}

        # Get approvers from policy or provided list
        if not approver_ids:
            approver_ids = self._get_approvers_for_entry(time_entry)

        if not approver_ids:
            return {"success": False, "message": "No approvers found for this time entry", "error": "no_approvers"}

        # Create approval request(s) - multi-level support
        approvals = []
        parent_approval = None

        for level, approver_id in enumerate(approver_ids, start=1):
            approval = TimeEntryApproval(
                time_entry_id=time_entry_id,
                requested_by=requested_by,
                status=ApprovalStatus.PENDING,
                request_comment=comment,
                parent_approval_id=parent_approval.id if parent_approval else None,
                approval_level=level,
            )
            db.session.add(approval)
            approvals.append(approval)
            parent_approval = approval

        db.session.commit()

        # Send notifications to approvers
        self._notify_approvers(approvals[0], approver_ids)

        return {"success": True, "message": "Approval requested", "approval": approvals[0].to_dict()}

    def approve(self, approval_id: int, approver_id: int, comment: str = None) -> Dict[str, Any]:
        """Approve a time entry"""
        approval = TimeEntryApproval.query.get(approval_id)
        if not approval:
            return {"success": False, "message": "Approval not found", "error": "not_found"}

        if approval.status != ApprovalStatus.PENDING:
            return {"success": False, "message": "Approval is not pending", "error": "invalid_status"}

        # Check if user is authorized to approve
        approver_ids = self._get_approvers_for_entry(approval.time_entry)
        if approver_id not in approver_ids:
            return {"success": False, "message": "Not authorized to approve", "error": "unauthorized"}

        # Approve current level
        approval.approve(approver_id, comment)

        # Check for next level approval
        child_approval = TimeEntryApproval.query.filter_by(
            parent_approval_id=approval.id, status=ApprovalStatus.PENDING
        ).first()

        if child_approval:
            # Notify next level approver
            self._notify_approvers(child_approval, [child_approval.requested_by])
            return {
                "success": True,
                "message": "Approved, awaiting next level approval",
                "approval": approval.to_dict(),
            }

        # All levels approved
        self._mark_entry_approved(approval.time_entry)

        return {"success": True, "message": "Time entry approved", "approval": approval.to_dict()}

    def reject(self, approval_id: int, approver_id: int, reason: str) -> Dict[str, Any]:
        """Reject a time entry approval"""
        approval = TimeEntryApproval.query.get(approval_id)
        if not approval:
            return {"success": False, "message": "Approval not found", "error": "not_found"}

        if approval.status != ApprovalStatus.PENDING:
            return {"success": False, "message": "Approval is not pending", "error": "invalid_status"}

        approval.reject(approver_id, reason)

        # Cancel any child approvals
        child_approvals = TimeEntryApproval.query.filter_by(
            parent_approval_id=approval.id, status=ApprovalStatus.PENDING
        ).all()

        for child in child_approvals:
            child.cancel()

        # Notify requester
        self._notify_requester(approval, "rejected", reason)

        return {"success": True, "message": "Time entry rejected", "approval": approval.to_dict()}

    def cancel_approval(self, approval_id: int, user_id: int) -> Dict[str, Any]:
        """Cancel an approval request"""
        approval = TimeEntryApproval.query.get(approval_id)
        if not approval:
            return {"success": False, "message": "Approval not found", "error": "not_found"}

        if approval.requested_by != user_id:
            return {"success": False, "message": "Not authorized to cancel", "error": "unauthorized"}

        if approval.status != ApprovalStatus.PENDING:
            return {"success": False, "message": "Cannot cancel non-pending approval", "error": "invalid_status"}

        approval.cancel()

        # Cancel child approvals
        child_approvals = TimeEntryApproval.query.filter_by(
            parent_approval_id=approval.id, status=ApprovalStatus.PENDING
        ).all()

        for child in child_approvals:
            child.cancel()

        return {"success": True, "message": "Approval cancelled", "approval": approval.to_dict()}

    def get_pending_approvals(self, approver_id: int = None) -> List[TimeEntryApproval]:
        """Get pending approvals for an approver"""
        query = TimeEntryApproval.query.filter_by(status=ApprovalStatus.PENDING)

        if approver_id:
            # Get approvals where user is an approver
            approver_ids = self._get_all_approver_ids(approver_id)
            # This would need a more sophisticated query in production
            # For now, return all pending approvals
            pass

        return query.order_by(TimeEntryApproval.requested_at.desc()).all()

    def bulk_approve(self, approval_ids: List[int], approver_id: int, comment: str = None) -> Dict[str, Any]:
        """Bulk approve multiple time entries"""
        results = []
        for approval_id in approval_ids:
            result = self.approve(approval_id, approver_id, comment)
            results.append({"approval_id": approval_id, **result})

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "message": f"Approved {success_count} of {len(approval_ids)} entries",
            "results": results,
        }

    def _get_approvers_for_entry(self, time_entry: TimeEntry) -> List[int]:
        """Get list of approver user IDs for a time entry"""
        # Check project-specific policy
        policy = ApprovalPolicy.query.filter_by(project_id=time_entry.project_id, enabled=True).first()

        if policy and policy.applies_to_entry(time_entry):
            return policy.get_approvers()

        # Check user-specific policy
        policy = ApprovalPolicy.query.filter_by(user_id=time_entry.user_id, enabled=True).first()

        if policy and policy.applies_to_entry(time_entry):
            return policy.get_approvers()

        # Check global policy
        policy = ApprovalPolicy.query.filter_by(applies_to_all=True, enabled=True).first()

        if policy and policy.applies_to_entry(time_entry):
            return policy.get_approvers()

        # Default: return project manager or admin
        project = time_entry.project
        if project and hasattr(project, "manager_id") and project.manager_id:
            return [project.manager_id]

        # Fallback to admins
        admins = User.query.filter_by(is_admin=True).all()
        return [admin.id for admin in admins]

    def _get_all_approver_ids(self, user_id: int) -> List[int]:
        """Get all policies where user is an approver"""
        policies = ApprovalPolicy.query.filter(ApprovalPolicy.enabled == True).all()

        approver_ids = []
        for policy in policies:
            if user_id in policy.get_approvers():
                approver_ids.append(policy.id)

        return approver_ids

    def _mark_entry_approved(self, time_entry: TimeEntry):
        """Mark time entry as approved"""
        # Add metadata to indicate approval
        if not hasattr(time_entry, "metadata") or not time_entry.metadata:
            time_entry.metadata = {}
        time_entry.metadata["approved"] = True
        time_entry.metadata["approved_at"] = datetime.utcnow().isoformat()
        db.session.commit()

    def _notify_approvers(self, approval: TimeEntryApproval, approver_ids: List[int]):
        """Send notifications to approvers"""
        from app.utils.notification_service import NotificationService

        service = NotificationService()
        for approver_id in approver_ids:
            service.send_notification(
                user_id=approver_id,
                title="Time Entry Approval Requested",
                message=f"Time entry {approval.time_entry_id} requires your approval",
                type="info",
                priority="normal",
            )

    def _notify_requester(self, approval: TimeEntryApproval, status: str, reason: str = None):
        """Send notification to requester"""
        from app.utils.notification_service import NotificationService

        service = NotificationService()
        message = f"Your time entry {approval.time_entry_id} has been {status}."
        if reason:
            message += f" Reason: {reason}"

        service.send_notification(
            user_id=approval.requested_by,
            title=f"Time Entry {status.title()}",
            message=message,
            type="success" if status == "approved" else "error",
            priority="normal",
        )
