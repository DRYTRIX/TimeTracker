# Integration System Refactoring Plan

## Issues Identified

1. **Double Pages**: `/calendar/integrations` and `/integrations` - duplicate functionality
2. **OAuth Requirements**: Some integrations (Trello) don't need OAuth but are using OAuth flow
3. **Global vs Per-User**: All integrations are currently per-user, but should be global (except Google Calendar)
4. **Setup Pages**: Need dedicated setup pages for each integration instead of all in one settings page

## Solution

### 1. Database Changes
- ✅ Migration 082: Add `is_global` flag to Integration model
- ✅ Make `user_id` nullable for global integrations
- ✅ Add constraint: global integrations must have `user_id = NULL`

### 2. Integration Classification

**Global Integrations** (shared across all users):
- Jira
- Slack  
- GitHub
- Outlook Calendar
- Microsoft Teams
- Asana
- Trello (API key based, not OAuth)
- GitLab
- QuickBooks
- Xero

**Per-User Integrations**:
- Google Calendar (each user connects their own)

### 3. OAuth vs API Key Requirements

**OAuth Required**:
- Jira (OAuth 2.0)
- Slack (OAuth 2.0)
- GitHub (OAuth 2.0)
- Google Calendar (OAuth 2.0) - per-user
- Outlook Calendar (OAuth 2.0)
- Microsoft Teams (OAuth 2.0)
- Asana (OAuth 2.0)
- GitLab (OAuth 2.0)
- QuickBooks (OAuth 2.0)
- Xero (OAuth 2.0)

**API Key Based** (no OAuth):
- Trello (API Key + Token)

### 4. Implementation Steps

1. ✅ Create migration for global integrations
2. ✅ Update Integration model
3. Update IntegrationService to handle global integrations
4. Create admin setup pages for each integration
5. Fix Trello connector to use API key setup (not OAuth)
6. Remove duplicate calendar integrations page
7. Update routes to use global integrations
8. Update integration list page to show global vs per-user

## Files to Modify

1. `app/models/integration.py` - Add is_global, make user_id nullable
2. `app/services/integration_service.py` - Handle global integrations
3. `app/routes/integrations.py` - Update to handle global
4. `app/routes/admin.py` - Add setup routes for each integration
5. `app/integrations/trello.py` - Fix to use API key setup
6. `app/routes/calendar.py` - Remove duplicate integrations page
7. `app/templates/integrations/` - Create setup templates

