"""
Service for invoice approval workflow business logic.
"""

from typing import Optional, List, Dict, Any
from app import db
from app.models import InvoiceApproval, Invoice, User
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent
from app.utils.timezone import now_in_app_timezone


class InvoiceApprovalService:
    """
    Service for invoice approval workflow operations.
    """

    def request_approval(
        self, invoice_id: int, requested_by: int, approvers: List[int], stages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Request approval for an invoice.

        Args:
            invoice_id: Invoice ID
            requested_by: User ID requesting approval
            approvers: List of user IDs who need to approve
            stages: Optional list of approval stages with custom configuration

        Returns:
            dict with 'success', 'message', and 'approval' keys
        """
        try:
            invoice = Invoice.query.get(invoice_id)
            if not invoice:
                return {"success": False, "message": "Invoice not found."}

            # Check if approval already exists
            existing = InvoiceApproval.query.filter_by(invoice_id=invoice_id, status="pending").first()

            if existing:
                return {"success": False, "message": "An approval request is already pending for this invoice."}

            # Create stages if not provided
            if not stages:
                stages = []
                for i, approver_id in enumerate(approvers):
                    stages.append(
                        {
                            "stage_number": i + 1,
                            "approver_id": approver_id,
                            "status": "pending",
                            "comments": None,
                            "approved_at": None,
                            "rejected_at": None,
                        }
                    )

            approval = InvoiceApproval(
                invoice_id=invoice_id,
                status="pending",
                stages=stages,
                current_stage=0,
                total_stages=len(stages),
                requested_by=requested_by,
                requested_at=now_in_app_timezone(),
            )

            db.session.add(approval)
            if not safe_commit("request_approval", {"invoice_id": invoice_id}):
                return {"success": False, "message": "Could not create approval request due to a database error."}

            emit_event(
                WebhookEvent.INVOICE_APPROVAL_REQUESTED,
                {
                    "invoice_id": invoice_id,
                    "approval_id": approval.id,
                    "requested_by": requested_by,
                    "total_stages": len(stages),
                },
            )

            return {"success": True, "message": "Approval request created successfully.", "approval": approval}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Error creating approval request: {str(e)}"}

    def approve(self, approval_id: int, approver_id: int, comments: Optional[str] = None) -> Dict[str, Any]:
        """
        Approve an invoice at the current stage.

        Returns:
            dict with 'success', 'message', and 'approval' keys
        """
        try:
            approval = InvoiceApproval.query.get(approval_id)
            if not approval:
                return {"success": False, "message": "Approval not found."}

            if approval.status != "pending":
                return {"success": False, "message": f"Approval is not pending (current status: {approval.status})."}

            # Get current stage
            current_stage_data = approval.stages[approval.current_stage] if approval.stages else None
            if not current_stage_data:
                return {"success": False, "message": "Invalid approval stage."}

            # Check if user is the approver for this stage
            if current_stage_data.get("approver_id") != approver_id:
                return {"success": False, "message": "You are not authorized to approve at this stage."}

            # Update current stage
            current_stage_data["status"] = "approved"
            current_stage_data["comments"] = comments
            current_stage_data["approved_at"] = now_in_app_timezone().isoformat()

            approval.stages[approval.current_stage] = current_stage_data

            # Move to next stage or complete
            if approval.current_stage < approval.total_stages - 1:
                approval.current_stage += 1
            else:
                # All stages approved
                approval.status = "approved"
                approval.approved_by = approver_id
                approval.approved_at = now_in_app_timezone()

                # Update invoice status
                invoice = Invoice.query.get(approval.invoice_id)
                if invoice and invoice.status == "draft":
                    invoice.status = "sent"

            if not safe_commit("approve_invoice", {"approval_id": approval_id}):
                return {"success": False, "message": "Could not update approval due to a database error."}

            # Emit event if fully approved
            if approval.status == "approved":
                emit_event(
                    WebhookEvent.INVOICE_APPROVED,
                    {"invoice_id": approval.invoice_id, "approval_id": approval.id, "approved_by": approver_id},
                )

            return {"success": True, "message": "Invoice approved successfully.", "approval": approval}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Error approving invoice: {str(e)}"}

    def reject(self, approval_id: int, rejector_id: int, reason: str) -> Dict[str, Any]:
        """
        Reject an invoice approval.

        Returns:
            dict with 'success', 'message', and 'approval' keys
        """
        try:
            approval = InvoiceApproval.query.get(approval_id)
            if not approval:
                return {"success": False, "message": "Approval not found."}

            if approval.status != "pending":
                return {"success": False, "message": f"Approval is not pending (current status: {approval.status})."}

            # Update approval
            approval.status = "rejected"
            approval.rejected_by = rejector_id
            approval.rejected_at = now_in_app_timezone()
            approval.rejection_reason = reason

            # Update current stage
            if approval.stages and approval.current_stage < len(approval.stages):
                current_stage_data = approval.stages[approval.current_stage]
                current_stage_data["status"] = "rejected"
                current_stage_data["comments"] = reason
                current_stage_data["rejected_at"] = now_in_app_timezone().isoformat()
                approval.stages[approval.current_stage] = current_stage_data

            if not safe_commit("reject_invoice", {"approval_id": approval_id}):
                return {"success": False, "message": "Could not update approval due to a database error."}

            emit_event(
                WebhookEvent.INVOICE_REJECTED,
                {
                    "invoice_id": approval.invoice_id,
                    "approval_id": approval.id,
                    "rejected_by": rejector_id,
                    "reason": reason,
                },
            )

            return {"success": True, "message": "Invoice approval rejected.", "approval": approval}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Error rejecting invoice: {str(e)}"}

    def get_approval(self, approval_id: int) -> Optional[InvoiceApproval]:
        """Get an approval by ID"""
        return InvoiceApproval.query.get(approval_id)

    def get_invoice_approval(self, invoice_id: int) -> Optional[InvoiceApproval]:
        """Get the current approval for an invoice"""
        return (
            InvoiceApproval.query.filter_by(invoice_id=invoice_id).order_by(InvoiceApproval.created_at.desc()).first()
        )

    def list_pending_approvals(self, user_id: Optional[int] = None) -> List[InvoiceApproval]:
        """
        List pending approvals.

        If user_id is provided, returns approvals where user is the current approver.
        Otherwise, returns all pending approvals.
        """
        query = InvoiceApproval.query.filter_by(status="pending")

        if user_id:
            # Filter to approvals where user is current approver
            # This requires checking the current stage's approver_id
            # For simplicity, we'll get all and filter in Python
            all_pending = query.all()
            result = []
            for approval in all_pending:
                if approval.stages and approval.current_stage < len(approval.stages):
                    current_stage = approval.stages[approval.current_stage]
                    if current_stage.get("approver_id") == user_id:
                        result.append(approval)
            return result

        return query.all()
