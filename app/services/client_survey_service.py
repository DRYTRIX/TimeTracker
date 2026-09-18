"""Client survey / NPS service."""

import logging
from typing import Optional

from app import db
from app.models.client_survey import ClientSurvey
from app.utils.db import safe_commit
from app.utils.email import send_template_email

logger = logging.getLogger(__name__)


class ClientSurveyService:
    """Create and send NPS surveys after project close or invoice payment."""

    def create_and_send(
        self,
        *,
        client_id: int,
        trigger: str,
        project_id: Optional[int] = None,
        invoice_id: Optional[int] = None,
        recipient_email: Optional[str] = None,
    ) -> Optional[ClientSurvey]:
        from app.models import Client, Contact

        client = Client.query.get(client_id)
        if not client:
            return None

        # Avoid duplicate open surveys for same trigger+entity
        existing = ClientSurvey.query.filter_by(
            client_id=client_id,
            trigger=trigger,
            project_id=project_id,
            invoice_id=invoice_id,
            responded_at=None,
        ).first()
        if existing and not existing.is_expired:
            return existing

        survey = ClientSurvey(
            client_id=client_id,
            trigger=trigger,
            project_id=project_id,
            invoice_id=invoice_id,
        )
        db.session.add(survey)
        if not safe_commit("create_client_survey", {"client_id": client_id, "trigger": trigger}):
            return None

        emails = []
        if recipient_email:
            emails = [recipient_email]
        else:
            if client.email:
                emails.append(client.email)
            for contact in Contact.query.filter_by(client_id=client_id, is_active=True).limit(10).all():
                if contact.email and contact.email not in emails:
                    emails.append(contact.email)

        from app.utils.urls import get_app_base_url

        base = (get_app_base_url() or "").rstrip("/")
        survey_url = f"{base}/client-portal/survey/{survey.token}" if base else f"/client-portal/survey/{survey.token}"

        for email in emails:
            try:
                send_template_email(
                    to=email,
                    subject="How did we do? Quick feedback",
                    template="email/client_survey.html",
                    client=client,
                    survey=survey,
                    survey_url=survey_url,
                )
            except Exception as exc:
                logger.error("Failed to send survey email to %s: %s", email, exc, exc_info=True)

        return survey

    def on_invoice_paid(self, invoice) -> Optional[ClientSurvey]:
        if not invoice or not getattr(invoice, "client_id", None):
            return None
        return self.create_and_send(
            client_id=invoice.client_id,
            trigger="invoice_paid",
            project_id=getattr(invoice, "project_id", None),
            invoice_id=invoice.id,
        )

    def on_project_closed(self, project) -> Optional[ClientSurvey]:
        if not project or not getattr(project, "client_id", None):
            return None
        return self.create_and_send(
            client_id=project.client_id,
            trigger="project_close",
            project_id=project.id,
        )
