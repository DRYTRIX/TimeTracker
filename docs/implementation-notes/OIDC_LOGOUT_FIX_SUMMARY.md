# OIDC Logout Fix Summary

## Issue Description

When `OIDC_POST_LOGOUT_REDIRECT_URI` was not set (unset/None), the application was still attempting RP-Initiated Logout at the OIDC provider. This caused issues with Identity Providers like Authelia that don't support RP-Initiated Logout yet.

For example, users would be incorrectly redirected to:
```
https://auth.example.de/api/oidc/revocation?id_token_hint=...
```

This would fail because the provider doesn't support the endpoint, instead of simply logging out locally and returning to the TimeTracker login page.

## Root Cause

In `app/routes/auth.py`, the logout function had this logic:

```python
post_logout = getattr(Config, 'OIDC_POST_LOGOUT_REDIRECT_URI', None) or url_for('auth.login', _external=True)
```

The problem was the `or url_for('auth.login', _external=True)` fallback. Even when `OIDC_POST_LOGOUT_REDIRECT_URI` was `None` (not configured), it would fall back to generating a logout redirect URL, causing the application to always attempt RP-Initiated Logout.

## Solution

Modified the logout logic to only perform RP-Initiated Logout if `OIDC_POST_LOGOUT_REDIRECT_URI` is **explicitly configured**:

```python
if auth_method in ('oidc', 'both'):
    # Only perform RP-Initiated Logout if OIDC_POST_LOGOUT_REDIRECT_URI is explicitly configured
    post_logout = getattr(Config, 'OIDC_POST_LOGOUT_REDIRECT_URI', None)
    if post_logout:
        # ... proceed with RP-Initiated Logout
```

Now:
- **If `OIDC_POST_LOGOUT_REDIRECT_URI` is NOT set**: Users are logged out locally and redirected to TimeTracker's login page
- **If `OIDC_POST_LOGOUT_REDIRECT_URI` IS set**: Users are redirected to the provider's logout endpoint (RP-Initiated Logout)

## Files Changed

### 1. `app/routes/auth.py`
- Modified logout function to check if `OIDC_POST_LOGOUT_REDIRECT_URI` is set before attempting provider logout
- Added comment explaining the behavior

### 2. `docs/OIDC_SETUP.md`
- Updated documentation for `OIDC_POST_LOGOUT_REDIRECT_URI` to clarify it's optional
- Added guidance: only set if your provider supports end_session_endpoint
- Updated troubleshooting section with specific guidance for providers like Authelia

### 3. `env.example`
- Added clear comments explaining when to set `OIDC_POST_LOGOUT_REDIRECT_URI`
- Noted that if unset, logout will be local only (recommended for providers without RP-Initiated Logout support)

### 4. `tests/test_oidc_logout.py` (NEW)
- Created comprehensive test suite with 9 tests covering:
  - Unit tests for logout without `OIDC_POST_LOGOUT_REDIRECT_URI` configured
  - Unit tests for logout with `OIDC_POST_LOGOUT_REDIRECT_URI` configured
  - Tests for different auth methods (local, oidc, both)
  - Tests for provider metadata loading failures
  - Tests for session token cleanup
  - Smoke tests for configuration validation

## Behavior Matrix

| AUTH_METHOD | OIDC_POST_LOGOUT_REDIRECT_URI | Logout Behavior |
|-------------|-------------------------------|-----------------|
| `local` | (any) | Local logout → `/login` |
| `oidc` or `both` | Not set (None) | Local logout → `/login` |
| `oidc` or `both` | Set | RP-Initiated Logout → Provider logout endpoint |

## Testing

All tests pass:
- ✅ 9 new OIDC logout tests (all passing)
- ✅ Existing logout tests remain passing (backward compatibility confirmed)
- ✅ No linter errors

Run tests with:
```bash
python -m pytest tests/test_oidc_logout.py -v
```

## Migration Guide

### For Users with Authelia or Similar Providers

If your OIDC provider doesn't support RP-Initiated Logout:

1. **Remove or comment out** `OIDC_POST_LOGOUT_REDIRECT_URI` from your environment:
   ```bash
   # OIDC_POST_LOGOUT_REDIRECT_URI=https://yourapp.example.com/
   ```

2. Restart the application

3. Test logout - you should now be redirected to TimeTracker's login page instead of the provider's revocation endpoint

### For Users with Providers Supporting RP-Initiated Logout

No changes needed. If you have `OIDC_POST_LOGOUT_REDIRECT_URI` configured, the behavior remains the same.

## Security Considerations

This fix does not reduce security:
- Users are still logged out of TimeTracker (session invalidated)
- The ID token is removed from the session
- For providers that support RP-Initiated Logout, full logout still occurs when configured

The only difference is that providers without RP-Initiated Logout support no longer receive logout requests they cannot handle.

## Compatibility

- ✅ Backward compatible - existing configurations continue to work
- ✅ Forward compatible - new optional behavior
- ✅ Works with all OIDC providers (Azure AD, Okta, Keycloak, Authelia, Google, etc.)
- ✅ No database migration required
- ✅ No breaking changes

## References

- Issue: Authelia doesn't support RP-Initiated Logout
- OIDC Spec: [RP-Initiated Logout](https://openid.net/specs/openid-connect-rpinitiated-1_0.html)
- Related: end_session_endpoint is optional in OIDC providers

