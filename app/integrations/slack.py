"""
Slack integration connector.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


class SlackConnector(BaseConnector):
    """Slack integration connector."""

    display_name = "Slack"
    description = "Send notifications and sync with Slack"
    icon = "slack"

    @property
    def provider_name(self) -> str:
        return "slack"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Slack OAuth authorization URL."""
        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials('slack')
        client_id = creds.get('client_id') or os.getenv('SLACK_CLIENT_ID')
        if not client_id:
            raise ValueError("SLACK_CLIENT_ID not configured")
        
        scopes = [
            'chat:write',
            'chat:write.public',
            'users:read',
            'channels:read',
            'groups:read'
        ]
        
        auth_url = "https://slack.com/oauth/v2/authorize"
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': ','.join(scopes),
            'state': state or ''
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials('slack')
        client_id = creds.get('client_id') or os.getenv('SLACK_CLIENT_ID')
        client_secret = creds.get('client_secret') or os.getenv('SLACK_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("Slack OAuth credentials not configured")
        
        token_url = "https://slack.com/api/oauth.v2.access"
        
        response = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        })
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get('ok'):
            raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")
        
        access_token = data.get('access_token')
        expires_in = data.get('expires_in', 0)
        expires_at = None
        if expires_in > 0:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            'access_token': access_token,
            'refresh_token': data.get('refresh_token'),
            'expires_at': expires_at,
            'token_type': 'Bearer',
            'scope': data.get('scope'),
            'extra_data': {
                'team_id': data.get('team', {}).get('id'),
                'team_name': data.get('team', {}).get('name'),
                'authed_user': data.get('authed_user', {})
            }
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")
        
        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials('slack')
        client_id = creds.get('client_id') or os.getenv('SLACK_CLIENT_ID')
        client_secret = creds.get('client_secret') or os.getenv('SLACK_CLIENT_SECRET')
        
        token_url = "https://slack.com/api/oauth.v2.access"
        
        response = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': self.credentials.refresh_token
        })
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get('ok'):
            raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")
        
        expires_at = None
        if 'expires_in' in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data['expires_in'])
        
        return {
            'access_token': data.get('access_token'),
            'refresh_token': data.get('refresh_token', self.credentials.refresh_token),
            'expires_at': expires_at
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Slack."""
        token = self.get_access_token()
        if not token:
            return {
                'success': False,
                'message': 'No access token available'
            }
        
        api_url = "https://slack.com/api/auth.test"
        
        try:
            response = requests.post(api_url, headers={
                'Authorization': f'Bearer {token}'
            })
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('ok'):
                return {
                    'success': True,
                    'message': f"Connected to {data.get('team', 'Unknown Team')}"
                }
            else:
                return {
                    'success': False,
                    'message': f"Slack API error: {data.get('error', 'Unknown error')}"
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Connection error: {str(e)}"
            }

    def sync_data(self, sync_type: str = 'full') -> Dict[str, Any]:
        """Sync data from Slack (channels, users, etc.)."""
        token = self.get_access_token()
        if not token:
            return {
                'success': False,
                'message': 'No access token available'
            }
        
        # This would sync Slack channels, users, etc.
        # Implementation depends on specific requirements
        
        return {
            'success': True,
            'message': 'Sync completed',
            'synced_items': 0
        }

    def send_message(self, channel: str, text: str) -> Dict[str, Any]:
        """Send a message to a Slack channel."""
        token = self.get_access_token()
        if not token:
            return {
                'success': False,
                'message': 'No access token available'
            }
        
        api_url = "https://slack.com/api/chat.postMessage"
        
        response = requests.post(api_url, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }, json={
            'channel': channel,
            'text': text
        })
        
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            return {
                'success': True,
                'message': 'Message sent successfully'
            }
        else:
            return {
                'success': False,
                'message': f"Slack API error: {data.get('error', 'Unknown error')}"
            }

