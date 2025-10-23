"""
PostHog Funnel Tracking Utilities

This module provides utilities for tracking multi-step conversion funnels
in your application. Use this to understand where users drop off in complex workflows.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import os


def is_funnel_tracking_enabled() -> bool:
    """Check if funnel tracking is enabled."""
    return bool(os.getenv("POSTHOG_API_KEY", ""))


def track_funnel_step(
    user_id: Any,
    funnel_name: str,
    step: str,
    properties: Optional[Dict[str, Any]] = None
) -> None:
    """
    Track a step in a conversion funnel.
    
    This creates events that can be visualized as funnels in PostHog,
    showing you where users drop off in multi-step processes.
    
    Args:
        user_id: The user ID (internal ID, not PII)
        funnel_name: Name of the funnel (e.g., 'onboarding', 'invoice_generation')
        step: Current step name (e.g., 'started', 'profile_completed')
        properties: Additional properties to track with this step
        
    Example:
        # User starts project creation
        track_funnel_step(user.id, "project_setup", "started")
        
        # User enters basic info
        track_funnel_step(user.id, "project_setup", "basic_info_entered", {
            "has_description": True
        })
        
        # User completes setup
        track_funnel_step(user.id, "project_setup", "completed")
    """
    if not is_funnel_tracking_enabled():
        return
    
    from app import track_event
    
    event_name = f"funnel.{funnel_name}.{step}"
    funnel_properties = {
        "funnel": funnel_name,
        "step": step,
        "step_timestamp": datetime.utcnow().isoformat(),
        **(properties or {})
    }
    
    track_event(user_id, event_name, funnel_properties)


# ============================================================================
# Predefined Funnels for TimeTracker
# ============================================================================

class Funnels:
    """
    Predefined funnel names for consistent tracking.
    
    Define your funnels here to avoid typos and enable autocomplete.
    """
    
    # User onboarding
    ONBOARDING = "onboarding"
    
    # Project management
    PROJECT_SETUP = "project_setup"
    
    # Invoice generation
    INVOICE_GENERATION = "invoice_generation"
    
    # Time tracking
    TIME_TRACKING_FLOW = "time_tracking_flow"
    
    # Export workflow
    EXPORT_WORKFLOW = "export_workflow"
    
    # Report generation
    REPORT_GENERATION = "report_generation"


# ============================================================================
# Onboarding Funnel
# ============================================================================

def track_onboarding_started(user_id: Any, properties: Optional[Dict] = None):
    """Track when user signs up / account is created."""
    track_funnel_step(user_id, Funnels.ONBOARDING, "signed_up", properties)


def track_onboarding_profile_completed(user_id: Any, properties: Optional[Dict] = None):
    """Track when user completes their profile."""
    track_funnel_step(user_id, Funnels.ONBOARDING, "profile_completed", properties)


def track_onboarding_first_project(user_id: Any, properties: Optional[Dict] = None):
    """Track when user creates their first project."""
    track_funnel_step(user_id, Funnels.ONBOARDING, "first_project_created", properties)


def track_onboarding_first_time_entry(user_id: Any, properties: Optional[Dict] = None):
    """Track when user logs their first time entry."""
    track_funnel_step(user_id, Funnels.ONBOARDING, "first_time_logged", properties)


def track_onboarding_first_timer(user_id: Any, properties: Optional[Dict] = None):
    """Track when user starts their first timer."""
    track_funnel_step(user_id, Funnels.ONBOARDING, "first_timer_started", properties)


def track_onboarding_week_1_completed(user_id: Any, properties: Optional[Dict] = None):
    """Track when user completes their first week of usage."""
    track_funnel_step(user_id, Funnels.ONBOARDING, "week_1_completed", properties)


# ============================================================================
# Project Setup Funnel
# ============================================================================

def track_project_setup_started(user_id: Any, properties: Optional[Dict] = None):
    """Track when user starts creating a new project."""
    track_funnel_step(user_id, Funnels.PROJECT_SETUP, "started", properties)


def track_project_setup_basic_info(user_id: Any, properties: Optional[Dict] = None):
    """Track when user enters basic project info."""
    track_funnel_step(user_id, Funnels.PROJECT_SETUP, "basic_info_entered", properties)


def track_project_setup_billing_configured(user_id: Any, properties: Optional[Dict] = None):
    """Track when user configures billing info."""
    track_funnel_step(user_id, Funnels.PROJECT_SETUP, "billing_configured", properties)


def track_project_setup_tasks_added(user_id: Any, properties: Optional[Dict] = None):
    """Track when user adds tasks to project."""
    track_funnel_step(user_id, Funnels.PROJECT_SETUP, "tasks_added", properties)


def track_project_setup_completed(user_id: Any, properties: Optional[Dict] = None):
    """Track when user completes project setup."""
    track_funnel_step(user_id, Funnels.PROJECT_SETUP, "completed", properties)


# ============================================================================
# Invoice Generation Funnel
# ============================================================================

def track_invoice_page_viewed(user_id: Any, properties: Optional[Dict] = None):
    """Track when user views invoice page."""
    track_funnel_step(user_id, Funnels.INVOICE_GENERATION, "page_viewed", properties)


def track_invoice_project_selected(user_id: Any, properties: Optional[Dict] = None):
    """Track when user selects project/client for invoice."""
    track_funnel_step(user_id, Funnels.INVOICE_GENERATION, "project_selected", properties)


def track_invoice_previewed(user_id: Any, properties: Optional[Dict] = None):
    """Track when user previews invoice."""
    track_funnel_step(user_id, Funnels.INVOICE_GENERATION, "invoice_previewed", properties)


def track_invoice_generated(user_id: Any, properties: Optional[Dict] = None):
    """Track when user generates/downloads invoice."""
    track_funnel_step(user_id, Funnels.INVOICE_GENERATION, "invoice_generated", properties)


# ============================================================================
# Time Tracking Flow
# ============================================================================

def track_time_tracking_started(user_id: Any, properties: Optional[Dict] = None):
    """Track when user opens time tracking interface."""
    track_funnel_step(user_id, Funnels.TIME_TRACKING_FLOW, "interface_opened", properties)


def track_time_tracking_timer_started(user_id: Any, properties: Optional[Dict] = None):
    """Track when user starts a timer."""
    track_funnel_step(user_id, Funnels.TIME_TRACKING_FLOW, "timer_started", properties)


def track_time_tracking_timer_stopped(user_id: Any, properties: Optional[Dict] = None):
    """Track when user stops a timer."""
    track_funnel_step(user_id, Funnels.TIME_TRACKING_FLOW, "timer_stopped", properties)


def track_time_tracking_notes_added(user_id: Any, properties: Optional[Dict] = None):
    """Track when user adds notes to time entry."""
    track_funnel_step(user_id, Funnels.TIME_TRACKING_FLOW, "notes_added", properties)


def track_time_tracking_saved(user_id: Any, properties: Optional[Dict] = None):
    """Track when time entry is saved."""
    track_funnel_step(user_id, Funnels.TIME_TRACKING_FLOW, "entry_saved", properties)


# ============================================================================
# Export Workflow
# ============================================================================

def track_export_started(user_id: Any, properties: Optional[Dict] = None):
    """Track when user initiates export."""
    track_funnel_step(user_id, Funnels.EXPORT_WORKFLOW, "started", properties)


def track_export_format_selected(user_id: Any, properties: Optional[Dict] = None):
    """Track when user selects export format."""
    track_funnel_step(user_id, Funnels.EXPORT_WORKFLOW, "format_selected", properties)


def track_export_filters_applied(user_id: Any, properties: Optional[Dict] = None):
    """Track when user applies filters to export."""
    track_funnel_step(user_id, Funnels.EXPORT_WORKFLOW, "filters_applied", properties)


def track_export_downloaded(user_id: Any, properties: Optional[Dict] = None):
    """Track when export is downloaded."""
    track_funnel_step(user_id, Funnels.EXPORT_WORKFLOW, "downloaded", properties)


# ============================================================================
# Report Generation
# ============================================================================

def track_report_page_viewed(user_id: Any, properties: Optional[Dict] = None):
    """Track when user views reports page."""
    track_funnel_step(user_id, Funnels.REPORT_GENERATION, "page_viewed", properties)


def track_report_type_selected(user_id: Any, properties: Optional[Dict] = None):
    """Track when user selects report type."""
    track_funnel_step(user_id, Funnels.REPORT_GENERATION, "type_selected", properties)


def track_report_filters_applied(user_id: Any, properties: Optional[Dict] = None):
    """Track when user applies filters."""
    track_funnel_step(user_id, Funnels.REPORT_GENERATION, "filters_applied", properties)


def track_report_generated(user_id: Any, properties: Optional[Dict] = None):
    """Track when report is generated."""
    track_funnel_step(user_id, Funnels.REPORT_GENERATION, "generated", properties)


# ============================================================================
# Helper Functions
# ============================================================================

def track_funnel_abandonment(
    user_id: Any,
    funnel_name: str,
    last_step_completed: str,
    reason: Optional[str] = None
) -> None:
    """
    Track when a user abandons a funnel.
    
    Args:
        user_id: User ID
        funnel_name: Name of the funnel
        last_step_completed: Last step the user completed before abandoning
        reason: Optional reason for abandonment (e.g., 'error', 'timeout')
    """
    from app import track_event
    
    track_event(user_id, f"funnel.{funnel_name}.abandoned", {
        "funnel": funnel_name,
        "last_step": last_step_completed,
        "abandonment_reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    })


def get_funnel_context(funnel_name: str, additional_context: Optional[Dict] = None) -> Dict:
    """
    Get standardized context for funnel events.
    
    Args:
        funnel_name: Name of the funnel
        additional_context: Additional context to include
        
    Returns:
        Dict of context properties
    """
    from flask import request
    
    context = {
        "funnel": funnel_name,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Add request context if available
    try:
        if request:
            context.update({
                "referrer": request.referrer,
                "user_agent": request.user_agent.string,
            })
    except Exception:
        pass
    
    # Add additional context
    if additional_context:
        context.update(additional_context)
    
    return context

