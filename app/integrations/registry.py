"""
Integration connector registry.
Registers all available connectors with the IntegrationService.
"""

from app.services.integration_service import IntegrationService
from app.integrations.jira import JiraConnector
from app.integrations.slack import SlackConnector
from app.integrations.github import GitHubConnector


def register_connectors():
    """Register all available connectors."""
    IntegrationService.register_connector("jira", JiraConnector)
    IntegrationService.register_connector("slack", SlackConnector)
    IntegrationService.register_connector("github", GitHubConnector)


# Auto-register on import
register_connectors()
