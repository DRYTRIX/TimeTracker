# OIDC Login Improvements

## Summary

This document describes the comprehensive improvements made to the OIDC (OpenID Connect) authentication system in TimeTracker to address token parsing issues and provide better debugging capabilities.

## Problem

The reported issue was that OIDC authentication was failing with empty claims:
```
2025-10-06 07:50:44,613 ERROR: OIDC callback missing issuer/sub: claims={} [in /app/app/routes/auth.py:268]
```

Even though Authelia (the OIDC provider) was processing the authentication successfully, the TimeTracker application was not receiving or parsing the ID token claims correctly.

## Root Cause

The OIDC callback handler was silently failing when parsing the ID token, with no detailed logging to understand what was happening. The code was catching exceptions but not logging them, making it impossible to debug in production.

## Improvements Made

### 1. Enhanced OIDC Callback Handler (`app/routes/auth.py`)

**Comprehensive Logging:**
- Added detailed logging at every step of the token exchange process
- Log token structure and available keys
- Log ID token parsing attempts and failures
- Log userinfo endpoint calls
- Added unverified JWT decoding for debugging (when verified parsing fails)

**Better Error Handling:**
- Parse ID token with proper error catching and logging
- Fall back to userinfo endpoint if ID token parsing fails
- Use userinfo as primary source if ID token is unavailable
- More detailed error messages to users and logs

**Key Changes:**
```python
# Before: Silent failure
try:
    claims = client.parse_id_token(token) or {}
except Exception:
    claims = {}

# After: Detailed logging and fallback
try:
    parsed = client.parse_id_token(token)
    if parsed:
        claims = parsed
        id_token_parsed = True
        current_app.logger.info("OIDC callback: ID token parsed successfully")
    else:
        current_app.logger.warning("OIDC callback: parse_id_token returned None/empty")
except Exception as e:
    current_app.logger.error("OIDC callback: Failed to parse ID token: %s", str(e))
    # Try manual decode for debugging
    try:
        import jwt
        unverified = jwt.decode(token['id_token'], options={"verify_signature": False})
        current_app.logger.info("OIDC callback: Unverified token claims: %s", list(unverified.keys()))
    except Exception as decode_err:
        current_app.logger.error("OIDC callback: Could not decode for debugging: %s", str(decode_err))
```

**Improved Claim Resolution:**
- Check both claims and userinfo for required fields
- Better logging of which claims are being requested
- Log the actual values extracted (with truncation for sensitive data)

### 2. Admin OIDC Debug Dashboard

Created a comprehensive admin interface for debugging OIDC configuration at `/admin/oidc/debug`.

**Features:**

**Configuration Overview:**
- Current OIDC status (enabled/disabled)
- Auth method setting
- Issuer URL
- Client ID status
- Client secret status (without revealing the secret)
- Redirect URI
- Configured scopes

**Claim Mapping Display:**
- Username claim
- Email claim
- Full name claim
- Groups claim
- Admin group mapping
- Admin email list
- Post-logout redirect URI

**Provider Metadata:**
- Automatically fetches and displays provider discovery document
- Shows all available endpoints (authorization, token, userinfo, etc.)
- Lists supported scopes
- Lists supported response types and grant types
- Shows supported claims
- Validates configured claims against supported claims

**OIDC Users List:**
- Shows all users who have logged in via OIDC
- Displays username, email, role, last login
- Shows OIDC subject (truncated for display)
- Quick link to detailed user view

**Environment Variables Reference:**
- Built-in documentation table showing all OIDC-related environment variables
- Descriptions and examples for each variable

### 3. OIDC Configuration Test Route (`/admin/oidc/test`)

Interactive testing tool that validates OIDC configuration:

**Tests Performed:**
1. **Discovery Document Access:** Fetches `.well-known/openid-configuration`
2. **OAuth Client Registration:** Verifies the client is properly registered
3. **Required Endpoints:** Checks for authorization, token, and userinfo endpoints
4. **Scope Validation:** Compares requested scopes against provider-supported scopes
5. **Claim Validation:** Checks if configured claims are in the provider's supported list

**User Feedback:**
- Each test shows ✓, ✗, or ⚠ status
- Detailed flash messages explain any issues
- All results logged for admin review

### 4. OIDC User Detail Page (`/admin/oidc/user/<id>`)

Detailed view of OIDC-authenticated users:

**Information Displayed:**
- User profile (username, email, full name, role, status)
- OIDC-specific data (issuer, subject)
- Activity statistics (projects, time entries, tasks)
- Authentication method indicator
- Quick links to edit user or view all users

### 5. Prominent OIDC Status Card on Admin Dashboard

Added a highly visible status card at the top of the admin dashboard that clearly shows OIDC status:

**Visual Indicators:**
- **ENABLED State:** Green card with green header, large checkmark icon, "ENABLED" text in green
- **DISABLED State:** Gray card with light header, X icon, "DISABLED" text in gray
- Color-coded for immediate recognition

**Information Displayed:**
- Current auth method (LOCAL/OIDC/BOTH) displayed prominently
- Configuration status with color-coded badges:
  - ✅ **Complete** (green) - All required settings configured
  - ⚠️ **Incomplete** (yellow) - OIDC enabled but missing settings
  - ➖ **Not configured** (gray) - OIDC is disabled
- Count of users authenticated via OIDC
- Warning alert when OIDC is enabled but configuration incomplete

**Quick Actions:**
- When enabled: "Test Config" and "View Details" buttons
- When disabled: "Setup Guide" button with instruction text
- Direct link to Debug Dashboard in card header

### 6. Dependencies

Added `PyJWT==2.8.0` to `requirements.txt` for debugging token decoding.

## Usage

### For Administrators

1. **Check OIDC Status on Admin Dashboard:**
   - Prominent status card at top of admin dashboard shows ENABLED/DISABLED
   - Green card = enabled and working, Gray card = disabled
   - Shows auth method, configuration status, and OIDC user count
   - Warning alert if OIDC is enabled but configuration incomplete

2. **Access the OIDC Debug Dashboard:**
   - Click "Debug Dashboard" or "View Details" button on status card
   - Or navigate to Admin Dashboard → OIDC Debug (yellow button in header)
   - Or directly: `/admin/oidc/debug`

3. **Test Your Configuration:**
   - Click "Test Config" button on status card or debug dashboard
   - Review all test results and fix any issues

4. **Monitor OIDC Users:**
   - View list of all OIDC-authenticated users in debug dashboard
   - Click "Details" to see full OIDC information for any user

5. **Check Logs:**
   - With improved logging, check application logs for detailed OIDC flow information
   - Look for messages prefixed with "OIDC callback:" or "OIDC Test:"

### For Users

When OIDC login fails, administrators now have:
- Detailed logs showing exactly where the failure occurred
- A dashboard to verify configuration is correct
- A test tool to validate provider connectivity
- Information about which users have successfully logged in via OIDC

## Environment Variables

All OIDC environment variables are documented in the debug dashboard. Key variables:

```bash
# Enable OIDC authentication
AUTH_METHOD=oidc  # or "both" for OIDC + local auth

# Provider configuration
OIDC_ISSUER=https://auth.example.com
OIDC_CLIENT_ID=timetracker
OIDC_CLIENT_SECRET=your-secret-here
OIDC_REDIRECT_URI=https://timetracker.example.com/auth/oidc/callback
OIDC_SCOPES="openid profile email groups"

# Claim mapping
OIDC_USERNAME_CLAIM=preferred_username
OIDC_EMAIL_CLAIM=email
OIDC_FULL_NAME_CLAIM=name
OIDC_GROUPS_CLAIM=groups

# Admin role mapping (optional)
OIDC_ADMIN_GROUP=timetracker_admin
OIDC_ADMIN_EMAILS=admin@example.com,boss@example.com
```

## Troubleshooting

### Empty Claims Error

If you see "OIDC callback missing issuer/sub: claims={}", check:

1. **Check Application Logs:** Look for detailed error messages about token parsing
2. **Use Test Configuration:** Run the OIDC test from the debug dashboard
3. **Verify Scopes:** Ensure your provider supports the requested scopes
4. **Check Claims:** Verify the provider includes the configured claims in ID token or userinfo
5. **Review Discovery Document:** Check that all required endpoints are present

### Common Issues

**Issue:** Token parsing fails
- **Solution:** Check if provider requires specific token validation settings
- **Debug:** Look for "Failed to parse ID token" in logs with error details

**Issue:** Missing claims
- **Solution:** Verify claim names match provider's configuration
- **Debug:** Check "Unverified token content" log entries to see what claims are actually present

**Issue:** Timeout fetching discovery document
- **Solution:** Check network connectivity and firewall rules
- **Debug:** Try accessing `.well-known/openid-configuration` manually

## Example: Authelia Configuration

For the specific Authelia setup mentioned in the issue:

```bash
# Authelia-specific settings
Environment=OIDC_ISSUER=https://auth.example.de
Environment=OIDC_CLIENT_ID=timetracker
Environment=OIDC_REDIRECT_URI=https://timetracker.example.de/auth/oidc/callback
Environment=OIDC_SCOPES="openid profile email groups"
Environment=OIDC_USERNAME_CLAIM=preferred_username
Environment=OIDC_EMAIL_CLAIM=email
Environment=OIDC_FULL_NAME_CLAIM=name
Environment=OIDC_GROUPS_CLAIM=groups
Environment=OIDC_ADMIN_GROUP=timetracker_admin
```

With the improved logging, if Authelia sends the token but parsing fails, you'll see:
1. "Token exchange successful" message
2. Exact error when parsing ID token
3. Unverified token contents showing what claims are actually present
4. Whether userinfo endpoint was successfully called as fallback
5. Exact list of claims keys received vs expected

## Testing

To test the OIDC improvements:

1. **Configuration Test:**
   ```bash
   # Visit /admin/oidc/debug
   # Click "Test Configuration"
   # Verify all tests pass
   ```

2. **Login Test:**
   ```bash
   # Attempt OIDC login
   # Check logs for detailed flow information
   # If it fails, check which step failed in the logs
   ```

3. **User Verification:**
   ```bash
   # After successful login, visit /admin/oidc/debug
   # Verify user appears in OIDC Users list
   # Check user detail page shows correct OIDC information
   ```

## Files Modified

- `app/routes/auth.py` - Enhanced OIDC callback handler with comprehensive logging
- `app/routes/admin.py` - Added OIDC debug routes and status information to dashboard
- `requirements.txt` - Added PyJWT for debugging
- `templates/admin/dashboard.html` - Added prominent OIDC status card and debug link
- `templates/admin/oidc_debug.html` - New OIDC debug dashboard (created)
- `templates/admin/oidc_user_detail.html` - New user detail page (created)

## Benefits

1. **Better Debugging:** Comprehensive logging makes it easy to identify exactly where OIDC flow fails
2. **Prominent Status Display:** Large, color-coded status card on admin dashboard instantly shows if OIDC is enabled/disabled
3. **Self-Service Testing:** Admins can test and validate configuration without developer help
4. **Transparency:** Clear visibility into what claims are received and how they're mapped
5. **Fallback Handling:** If ID token parsing fails, system falls back to userinfo endpoint
6. **User Tracking:** Easy to see which users are using OIDC authentication
7. **Documentation:** Built-in reference for all OIDC environment variables
8. **Configuration Validation:** Real-time status shows if OIDC configuration is complete or missing required settings

## Security Notes

- Client secrets are never displayed in the UI (only "Set" or "Not Set")
- Sensitive token data is truncated in logs
- Unverified token decoding is only for debugging and doesn't affect authentication
- All OIDC routes require admin authentication
- OIDC subject (sub) values are displayed in user details for audit purposes
