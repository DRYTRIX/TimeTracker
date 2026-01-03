"""
GitHub integration connector.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


def _env_if_allowed(name: str) -> str:
    """Prevent global env fallbacks for tenant-scoped credentials in SaaS multi-tenant mode."""
    try:
        from flask import current_app

        if bool(current_app.config.get("SAAS_MODE")) and (current_app.config.get("TENANCY_MODE") == "multi"):
            return ""
    except Exception:
        pass
    return os.getenv(name) or ""


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
        client_id = creds.get("client_id") or _env_if_allowed("GITHUB_CLIENT_ID")
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
        client_id = creds.get("client_id") or _env_if_allowed("GITHUB_CLIENT_ID")
        client_secret = creds.get("client_secret") or _env_if_allowed("GITHUB_CLIENT_SECRET")

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
        import logging

        logger = logging.getLogger(__name__)

        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available. Please reconnect the integration."}

        # Get repositories from config
        repos_str = self.integration.config.get("repositories", "")
        if not repos_str:
            # Get user's repositories
            try:
                repos_response = requests.get(
                    "https://api.github.com/user/repos",
                    headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
                    timeout=30
                )
                if repos_response.status_code == 200:
                    repos = repos_response.json()
                    repos_list = [f"{r['owner']['login']}/{r['name']}" for r in repos[:10]]  # Limit to 10 repos
                elif repos_response.status_code == 401:
                    return {"success": False, "message": "GitHub authentication failed. Please reconnect the integration."}
                else:
                    error_msg = f"Could not fetch repositories: {repos_response.status_code} - {repos_response.text[:200]}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}
            except requests.exceptions.Timeout:
                return {"success": False, "message": "GitHub API request timed out. Please try again."}
            except requests.exceptions.ConnectionError as e:
                return {"success": False, "message": f"Failed to connect to GitHub API: {str(e)}"}
            except Exception as e:
                logger.error(f"Error fetching repositories: {e}", exc_info=True)
                return {"success": False, "message": f"Error fetching repositories: {str(e)}"}
        else:
            repos_list = [r.strip() for r in repos_str.split(",") if r.strip()]

        if not repos_list:
            return {"success": False, "message": "No repositories configured or found"}

        synced_count = 0
        errors = []

        try:
            for repo in repos_list:
                try:
                    if "/" not in repo:
                        errors.append(f"Invalid repository format: {repo} (expected owner/repo)")
                        continue
                    
                    owner, repo_name = repo.split("/", 1)

                    # Find or create project
                    project = Project.query.filter_by(user_id=self.integration.user_id, name=repo).first()

                    if not project:
                        try:
                            project = Project(
                                name=repo,
                                description=f"GitHub repository: {repo}",
                                user_id=self.integration.user_id,
                                status="active",
                            )
                            db.session.add(project)
                            db.session.flush()
                        except Exception as e:
                            errors.append(f"Error creating project for {repo}: {str(e)}")
                            logger.error(f"Error creating project for {repo}: {e}", exc_info=True)
                            continue

                    # Fetch issues
                    try:
                        issues_response = requests.get(
                            f"https://api.github.com/repos/{repo}/issues",
                            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
                            params={"state": "open", "per_page": 100},
                            timeout=30
                        )

                        if issues_response.status_code == 404:
                            errors.append(f"Repository {repo} not found or access denied")
                            continue
                        elif issues_response.status_code == 401:
                            errors.append(f"Authentication failed for repository {repo}")
                            continue
                        elif issues_response.status_code != 200:
                            error_text = issues_response.text[:200] if issues_response.text else ""
                            errors.append(f"Error fetching issues for {repo}: {issues_response.status_code} - {error_text}")
                            continue

                        issues = issues_response.json()
                    except requests.exceptions.Timeout:
                        errors.append(f"Timeout fetching issues for {repo}")
                        continue
                    except requests.exceptions.ConnectionError as e:
                        errors.append(f"Connection error for {repo}: {str(e)}")
                        continue
                    except Exception as e:
                        errors.append(f"Error fetching issues for {repo}: {str(e)}")
                        logger.error(f"Error fetching issues for {repo}: {e}", exc_info=True)
                        continue

                    for issue in issues:
                        try:
                            issue_number = issue.get("number")
                            issue_title = issue.get("title", "")

                            if not issue_number:
                                continue

                            # Find or create task
                            task = Task.query.filter_by(
                                project_id=project.id, name=f"#{issue_number}: {issue_title}"
                            ).first()

                            if not task:
                                try:
                                    task = Task(
                                        project_id=project.id,
                                        name=f"#{issue_number}: {issue_title}",
                                        description=issue.get("body", ""),
                                        status="todo",
                                        notes=f"GitHub Issue: {issue.get('html_url', '')}",
                                    )
                                    db.session.add(task)
                                    db.session.flush()
                                except Exception as e:
                                    errors.append(f"Error creating task for issue #{issue_number} in {repo}: {str(e)}")
                                    logger.error(f"Error creating task for issue #{issue_number} in {repo}: {e}", exc_info=True)
                                    continue

                            # Store GitHub issue info in task metadata
                            try:
                                if not hasattr(task, "metadata") or not task.metadata:
                                    task.metadata = {}
                                task.metadata["github_repo"] = repo
                                task.metadata["github_issue_number"] = issue_number
                                task.metadata["github_issue_id"] = issue.get("id")
                                task.metadata["github_issue_url"] = issue.get("html_url")
                            except Exception as e:
                                logger.warning(f"Error updating task metadata for issue #{issue_number}: {e}")

                            synced_count += 1
                        except Exception as e:
                            errors.append(f"Error syncing issue #{issue.get('number', 'unknown')} in {repo}: {str(e)}")
                            logger.error(f"Error syncing issue #{issue.get('number', 'unknown')} in {repo}: {e}", exc_info=True)
                except ValueError as e:
                    errors.append(f"Invalid repository format: {repo} - {str(e)}")
                except Exception as e:
                    errors.append(f"Error syncing repository {repo}: {str(e)}")
                    logger.error(f"Error syncing repository {repo}: {e}", exc_info=True)

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error_msg = f"Database error during sync: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                return {"success": False, "message": error_msg, "synced_items": synced_count, "errors": errors}

            if errors:
                return {
                    "success": True,
                    "message": f"Sync completed with {len(errors)} error(s). Synced {synced_count} issues.",
                    "synced_items": synced_count,
                    "errors": errors,
                }
            
            return {
                "success": True,
                "message": f"Sync completed. Synced {synced_count} issues.",
                "synced_items": synced_count,
                "errors": errors,
            }
        except Exception as e:
            logger.error(f"GitHub sync failed: {e}", exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                pass
            return {"success": False, "message": f"Sync failed: {str(e)}", "errors": errors}

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str], raw_body: Optional[bytes] = None) -> Dict[str, Any]:
        """Handle incoming webhook from GitHub."""
        import hmac
        import hashlib
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Verify webhook signature if secret is configured
            signature = headers.get("X-Hub-Signature-256", "")
            if signature:
                # Get webhook secret from integration config
                webhook_secret = self.integration.config.get("webhook_secret") if self.integration else None
                
                if webhook_secret:
                    # GitHub sends signature as "sha256=<hash>"
                    if not signature.startswith("sha256="):
                        logger.warning("GitHub webhook signature format invalid (expected sha256= prefix)")
                        return {
                            "success": False,
                            "message": "Invalid webhook signature format"
                        }
                    
                    signature_hash = signature[7:]  # Remove "sha256=" prefix
                    
                    # GitHub signs the raw request body bytes, not the parsed JSON
                    # This is critical for signature verification to work correctly
                    if raw_body is None:
                        # Fallback: try to reconstruct from payload (not ideal but better than nothing)
                        import json
                        raw_body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
                        logger.warning("GitHub webhook: Using reconstructed payload for signature verification (raw body not available)")
                    
                    # Compute expected signature using raw body bytes
                    expected_signature = hmac.new(
                        webhook_secret.encode('utf-8'),
                        raw_body,
                        hashlib.sha256
                    ).hexdigest()
                    
                    # Use constant-time comparison to prevent timing attacks
                    if not hmac.compare_digest(signature_hash, expected_signature):
                        logger.warning("GitHub webhook signature verification failed")
                        return {
                            "success": False,
                            "message": "Webhook signature verification failed"
                        }
                    
                    logger.debug("GitHub webhook signature verified successfully")
                else:
                    # Signature provided but no secret configured - reject for security
                    logger.warning("GitHub webhook signature provided but no secret configured - rejecting webhook")
                    return {
                        "success": False,
                        "message": "Webhook secret not configured"
                    }
            else:
                # No signature provided - check if secret is configured
                webhook_secret = self.integration.config.get("webhook_secret") if self.integration else None
                if webhook_secret:
                    # Secret configured but no signature - reject for security
                    logger.warning("GitHub webhook secret configured but no signature provided - rejecting webhook")
                    return {
                        "success": False,
                        "message": "Webhook signature required but not provided"
                    }

            # Process webhook event
            action = payload.get("action")
            event_type = headers.get("X-GitHub-Event", "")

            if event_type == "issues":
                issue = payload.get("issue", {})
                issue_number = issue.get("number")
                repo = payload.get("repository", {}).get("full_name", "")

                return {
                    "success": True,
                    "message": f"Webhook received for issue #{issue_number} in {repo}",
                    "event_type": f"{event_type}.{action}",
                }
            elif event_type == "pull_request":
                pr = payload.get("pull_request", {})
                pr_number = pr.get("number")
                repo = payload.get("repository", {}).get("full_name", "")

                return {
                    "success": True,
                    "message": f"Webhook received for PR #{pr_number} in {repo}",
                    "event_type": f"{event_type}.{action}",
                }

            return {"success": True, "message": f"Webhook processed: {event_type}"}
        except ValueError as e:
            # Handle validation errors
            logger.error(f"GitHub webhook validation error: {e}")
            return {"success": False, "message": f"Webhook validation error: {str(e)}"}
        except Exception as e:
            # Handle all other errors
            logger.error(f"GitHub webhook processing error: {e}", exc_info=True)
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
                    "help": "Comma-separated list of repositories to sync (e.g., 'octocat/Hello-World, owner/repo'). Leave empty to sync all accessible repositories.",
                    "description": "Which GitHub repositories to sync",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "github_to_timetracker", "label": "GitHub → TimeTracker (Import only)"},
                        {"value": "timetracker_to_github", "label": "TimeTracker → GitHub (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "github_to_timetracker",
                    "description": "Choose how data flows between GitHub and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "issues", "label": "Issues"},
                        {"value": "pull_requests", "label": "Pull Requests"},
                        {"value": "projects", "label": "Projects (Repositories)"},
                    ],
                    "default": ["issues"],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "issue_states",
                    "type": "array",
                    "label": "Issue States to Sync",
                    "options": [
                        {"value": "open", "label": "Open Issues"},
                        {"value": "closed", "label": "Closed Issues"},
                        {"value": "all", "label": "All Issues"},
                    ],
                    "default": ["open"],
                    "description": "Which issue states to include in sync",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync when webhooks are received from GitHub",
                },
                {
                    "name": "sync_interval",
                    "type": "select",
                    "label": "Sync Schedule",
                    "options": [
                        {"value": "manual", "label": "Manual only"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily"},
                        {"value": "weekly", "label": "Weekly"},
                    ],
                    "default": "manual",
                    "description": "How often to automatically sync data",
                },
                {
                    "name": "create_projects",
                    "type": "boolean",
                    "label": "Create Projects",
                    "default": True,
                    "description": "Automatically create projects in TimeTracker from GitHub repositories",
                },
                {
                    "name": "webhook_secret",
                    "label": "Webhook Secret",
                    "type": "password",
                    "required": False,
                    "placeholder": "Enter webhook secret from GitHub",
                    "help": "Secret token for verifying webhook signatures. Configure this in your GitHub repository webhook settings.",
                    "description": "Security token for webhook verification",
                },
            ],
            "required": [],
            "sections": [
                {
                    "title": "Repository Settings",
                    "description": "Configure which repositories to sync",
                    "fields": ["repositories", "create_projects"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "issue_states", "auto_sync", "sync_interval"],
                },
                {
                    "title": "Webhook Settings",
                    "description": "Configure webhook security",
                    "fields": ["webhook_secret"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "github_to_timetracker",
                "sync_items": ["issues"],
            },
        }
