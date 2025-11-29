"""
Integration connector registry.
Registers all available connectors with the IntegrationService.
"""

from app.services.integration_service import IntegrationService
from app.integrations.jira import JiraConnector
from app.integrations.slack import SlackConnector
from app.integrations.github import GitHubConnector
from app.integrations.google_calendar import GoogleCalendarConnector
from app.integrations.outlook_calendar import OutlookCalendarConnector
from app.integrations.microsoft_teams import MicrosoftTeamsConnector
from app.integrations.asana import AsanaConnector
from app.integrations.trello import TrelloConnector
from app.integrations.gitlab import GitLabConnector
from app.integrations.quickbooks import QuickBooksConnector
from app.integrations.xero import XeroConnector


def register_connectors():
    """Register all available connectors."""
    IntegrationService.register_connector("jira", JiraConnector)
    IntegrationService.register_connector("slack", SlackConnector)
    IntegrationService.register_connector("github", GitHubConnector)
    IntegrationService.register_connector("google_calendar", GoogleCalendarConnector)
    IntegrationService.register_connector("outlook_calendar", OutlookCalendarConnector)
    IntegrationService.register_connector("microsoft_teams", MicrosoftTeamsConnector)
    IntegrationService.register_connector("asana", AsanaConnector)
    IntegrationService.register_connector("trello", TrelloConnector)
    IntegrationService.register_connector("gitlab", GitLabConnector)
    IntegrationService.register_connector("quickbooks", QuickBooksConnector)
    IntegrationService.register_connector("xero", XeroConnector)


# Auto-register on import
register_connectors()
