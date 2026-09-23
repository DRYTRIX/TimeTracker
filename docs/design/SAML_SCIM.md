# SAML SSO login + SCIM 2.0 provisioning

Enterprise identity design: **SAML 2.0** for browser login and **SCIM 2.0** for automated user lifecycle from Okta, Azure AD, Google Workspace, etc.

Scaffolding: `app/routes/api_scim.py` (Users list stub), feature flag `SCIM_ENABLED`. SAML is design-only until `python3-saml` integration is scheduled.

## SAML 2.0 (login)

### Library

- **[python3-saml](https://github.com/SAML-Toolkits/python3-saml)** (`onelogin.saml2`) for SP-initiated and IdP-initiated flows.
- Settings stored in `Settings` or dedicated `saml_idp_configs` table (future migration).

### Flow

1. User clicks “Sign in with SSO (SAML)” on `/auth/login`.
2. SP generates AuthnRequest → redirect to IdP.
3. IdP POSTs SAMLResponse to `/auth/saml/acs` (Assertion Consumer Service).
4. Validate signature, `NotOnOrAfter`, audience, recipient; map attributes → `User` (create or update).
5. Establish Flask-Login session; honor `AUTH_METHOD` matrix (`saml`, `all`, etc.—extend `app/config.py` enum in implementation PR).

### Attribute mapping (defaults)

| SAML attribute | User field |
|----------------|------------|
| `NameID` or `email` | `email` (lookup key) |
| `givenName` + `sn` or `displayName` | `full_name` |
| `memberOf` / custom groups claim | RBAC via group → role map (mirror `OIDC_ROLE_GROUP_MAP`) |

### Endpoints (target)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/saml/login` | Initiate SSO |
| POST | `/auth/saml/acs` | Consume assertion |
| GET | `/auth/saml/metadata` | SP metadata XML for IdP upload |
| GET | `/auth/saml/slo` | Single logout (optional phase 2) |

### Config (env / settings)

- `SAML_ENABLED`, `SAML_SP_ENTITY_ID`, `SAML_SP_ACS_URL`, IdP metadata URL or XML blob, x509 cert for signing (optional).

### Security

- Reject unsigned assertions unless explicitly allowed in dev.
- Clock skew tolerance ≤ 120s.
- Do not enable SAML and weak local passwords for the same admin accounts without MFA policy.

## SCIM 2.0 (provisioning)

### Scope

- **Users** resource (create, update, deactivate, list, filter by `userName`).
- **Groups** (optional phase 2) mapped to `Role` or team labels—not LDAP groups duplication.

### Auth

- Bearer token (`SCIM_BEARER_TOKEN` env) validated on every request; future: per-tenant tokens when multi-tenant lands.
- Separate from personal API tokens and OAuth (see `OAUTH2_API_APPS.md`).

### Base URL

`/scim/v2` (RFC 7644).

### Endpoints (target)

| Method | Path | Status |
|--------|------|--------|
| GET | `/scim/v2/ServiceProviderConfig` | Stub → minimal config |
| GET | `/scim/v2/Schemas` | Stub → User schema |
| GET | `/scim/v2/Users` | **Stub:** empty ListResponse when `SCIM_ENABLED` |
| GET | `/scim/v2/Users/{id}` | 501 → implement with User.id |
| POST | `/scim/v2/Users` | Create user + send invite |
| PUT/PATCH | `/scim/v2/Users/{id}` | Update profile, active flag |
| DELETE | `/scim/v2/Users/{id}` | Soft-deactivate (`is_active=false`) |

### User mapping

| SCIM | TimeTracker |
|------|-------------|
| `userName` | `username` (unique) |
| `name.givenName` / `name.familyName` | `full_name` |
| `emails[type eq "work"].value` | `email` |
| `active` | `is_active` |
| `externalId` | New column `scim_external_id` (future migration) |
| `id` | Stringified `users.id` (or UUID if migrated) |

### Deprovisioning

- `active: false` → disable login, revoke API tokens, stop timers (policy TBD in admin settings).

## Coexistence with LDAP / OIDC

| Method | Use case |
|--------|----------|
| OIDC | Cloud IdPs with modern OAuth/OIDC |
| SAML | Legacy enterprise IdPs |
| LDAP | Bind auth + optional sync |
| SCIM | HR-driven provisioning regardless of login protocol |

`AUTH_METHOD` should document allowed combinations; SCIM is independent of login method.

## Implementation phases

1. **Scaffolding:** SCIM GET Users stub + this doc + `SCIM_ENABLED` flag.
2. SAML ACS + metadata + admin settings UI.
3. SCIM full Users CRUD + audit logs.
4. Groups ↔ roles (optional).
5. End-to-end tests with Okta/Azure AD sandbox.

## References

- RFC 7643 (SCIM core schema), RFC 7644 (SCIM protocol)
- Existing OIDC: `app/routes/auth.py`, `app/config.py` OIDC_* settings
- Stub route: `app/routes/api_scim.py`
