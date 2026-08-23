"""Hook first invoice send for support soft prompts."""

from __future__ import annotations


def queue_first_invoice_support_prompt(user_id: int, *, first_send: bool = False) -> None:
    """Queue a one-shot support prompt when the user sends their first invoice."""
    from flask import session

    from app.services.support_prompt_service import SupportPromptService

    SupportPromptService.queue_first_invoice_prompt(session, user_id, first_send=first_send)
