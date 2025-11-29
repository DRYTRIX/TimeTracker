"""
GitHub integration connector.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


class GitHubConnector(BaseConnector):
    """GitHub integration connector."""

    display_name = "GitHub"
    description = "Sync issues and track time from GitHub"
    icon = "github"

    @property
    def provider_name(self) -> str:
        return "github"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get GitHub OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("github")
        client_id = creds.get("client_id") or os.getenv("GITHUB_CLIENT_ID")
        if not client_id:
            raise ValueError("GITHUB_CLIENT_ID not configured")

        scopes = ["repo", "issues:read", "issues:write", "user:email"]

        auth_url = "https://github.com/login/oauth/authorize"
        params = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": " ".join(scopes), "state": state or ""}

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("github")
        client_id = creds.get("client_id") or os.getenv("GITHUB_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GITHUB_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("GitHub OAuth credentials not configured")

        token_url = "https://github.com/login/oauth/access_token"

        response = requests.post(
            token_url,
            data={"client_id": client_id, "client_secret": client_secret, "code": code, "redirect_uri": redirect_uri},
            headers={"Accept": "application/json"},
        )

        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise ValueError(f"GitHub OAuth error: {data.get('error_description', data.get('error'))}")

        # GitHub tokens don't expire by default, but can be configured
        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        # Get user info
        access_token = data.get("access_token")
        user_info = {}
        if access_token:
            try:
                user_response = requests.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {access_token}", "Accept": "application/vnd.github.v3+json"},
                )
                if user_response.status_code == 200:
                    user_info = user_response.json()
            except Exception:
                pass

        return {
            "access_token": access_token,
            "refresh_token": data.get("refresh_token"),  # GitHub doesn't provide refresh tokens by default
            "expires_at": expires_at,
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope"),
            "extra_data": {
                "user_login": user_info.get("login"),
                "user_name": user_info.get("name"),
                "user_email": user_info.get("email"),
            },
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token (GitHub tokens typically don't expire)."""
        # GitHub tokens don't expire by default
        # If using GitHub Apps, refresh would be handled differently
        if not self.credentials or not self.credentials.access_token:
            raise ValueError("No access token available")

        # For now, just return the existing token
        # In production, implement proper refresh if using GitHub Apps
        return {
            "access_token": self.credentials.access_token,
            "refresh_token": self.credentials.refresh_token,
            "expires_at": self.credentials.expires_at,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to GitHub."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        api_url = "https://api.github.com/user"

        try:
            response = requests.get(
                api_url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            )

            if response.status_code == 200:
                user_data = response.json()
                return {"success": True, "message": f"Connected as {user_data.get('login', 'Unknown')}"}
            else:
                return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync issues from GitHub repositories and create tasks."""
        from app.models import Task, Project
        from app import db
        from datetime import datetime, timedelta

        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        # Get repositories from config
        repos_str = self.integration.config.get("repositories", "")
        if not repos_str:
            # Get user's repositories
            repos_response = requests.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"token {token}"}
            )
            if repos_response.status_code == 200:
                repos = repos_response.json()
                repos_list = [f"{r['owner']['login']}/{r['name']}" for r in repos[:10]]  # Limit to 10 repos
            else:
                return {"success": False, "message": "Could not fetch repositories"}
        else:
            repos_list = [r.strip() for r in repos_str.split(",") if r.strip()]

        synced_count = 0
        errors = []

        try:
            for repo in repos_list:
                try:
                    owner, repo_name = repo.split("/")
                    
                    # Find or create project
                    project = Project.query.filter_by(
                        user_id=self.integration.user_id,
                        name=repo
                    ).first()
                    
                    if not project:
                        project = Project(
                            name=repo,
                            description=f"GitHub repository: {repo}",
                            user_id=self.integration.user_id,
                            status="active"
                        )
                        db.session.add(project)
                        db.session.flush()

                    # Fetch issues
                    issues_response = requests.get(
                        f"https://api.github.com/repos/{repo}/issues",
                        headers={
                            "Authorization": f"token {token}",
                            "Accept": "application/vnd.github.v3+json"
                        },
                        params={
                            "state": "open",
                            "per_page": 100
                        }
                    )

                    if issues_response.status_code != 200:
                        errors.append(f"Error fetching issues for {repo}: {issues_response.status_code}")
                        continue

                    issues = issues_response.json()

                    for issue in issues:
                        try:
                            issue_number = issue.get("number")
                            issue_title = issue.get("title", "")
                            
                            # Find or create task
                            task = Task.query.filter_by(
                                project_id=project.id,
                                name=f"#{issue_number}: {issue_title}"
                            ).first()

                            if not task:
                                task = Task(
                                    project_id=project.id,
                                    name=f"#{issue_number}: {issue_title}",
                                    description=issue.get("body", ""),
                                    status="todo",
                                    notes=f"GitHub Issue: {issue.get('html_url', '')}"
                                )
                                db.session.add(task)
                                db.session.flush()

                            # Store GitHub issue info in task metadata
                            if not hasattr(task, 'metadata') or not task.metadata:
                                task.metadata = {}
                            task.metadata['github_repo'] = repo
                            task.metadata['github_issue_number'] = issue_number
                            task.metadata['github_issue_id'] = issue.get("id")
                            task.metadata['github_issue_url'] = issue.get("html_url")

                            synced_count += 1
                        except Exception as e:
                            errors.append(f"Error syncing issue #{issue.get('number', 'unknown')} in {repo}: {str(e)}")
                except ValueError:
                    errors.append(f"Invalid repository format: {repo}")
                except Exception as e:
                    errors.append(f"Error syncing repository {repo}: {str(e)}")

            db.session.commit()

            return {
                "success": True,
                "message": f"Sync completed. Synced {synced_count} issues.",
                "synced_items": synced_count,
                "errors": errors
            }
        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle incoming webhook from GitHub."""
        try:
            # Verify webhook signature if secret is configured
            signature = headers.get("X-Hub-Signature-256", "")
            if signature:
                # Signature verification would go here
                pass

            action = payload.get("action")
            event_type = headers.get("X-GitHub-Event", "")

            if event_type == "issues":
                issue = payload.get("issue", {})
                issue_number = issue.get("number")
                repo = payload.get("repository", {}).get("full_name", "")

                return {
                    "success": True,
                    "message": f"Webhook received for issue #{issue_number} in {repo}",
                    "event_type": f"{event_type}.{action}"
                }
            elif event_type == "pull_request":
                pr = payload.get("pull_request", {})
                pr_number = pr.get("number")
                repo = payload.get("repository", {}).get("full_name", "")

                return {
                    "success": True,
                    "message": f"Webhook received for PR #{pr_number} in {repo}",
                    "event_type": f"{event_type}.{action}"
                }

            return {"success": True, "message": f"Webhook processed: {event_type}"}
        except Exception as e:
            return {"success": False, "message": f"Error processing webhook: {str(e)}"}

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "repositories",
                    "label": "Repositories",
                    "type": "text",
                    "required": False,
                    "placeholder": "owner/repo1, owner/repo2",
                    "help": "Comma-separated list of repositories to sync",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": True,
                    "description": "Automatically sync when webhooks are received"
                }
            ],
            "required": [],
        }
