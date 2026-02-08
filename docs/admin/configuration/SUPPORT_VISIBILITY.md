# Support / Donate visibility

This guide describes how to configure the optional **Support visibility** feature. When enabled, users can hide donate and support prompts (sidebar link, header button, support banner, and donate widgets) by entering a **code** that is issued per installation.

## What users see

- In **Settings → Support visibility**, each user sees a **System ID** (a stable UUID for your installation) and a field to enter a code.
- After a valid code is entered and verified, donate and support UI is hidden for that user and the setting is saved.
- The System ID does not change between restarts; it identifies your instance so you can issue the correct code.

## Server configuration

You can enable verification in two ways. Only one is required.

### Option A: Public key (recommended)

The server stores **only a public key**. No secret is on the server; codes are generated offline using the matching private key. This is the most secure option.

| Variable | Description |
|----------|-------------|
| `DONATE_HIDE_PUBLIC_KEY_FILE` | Path to a file containing the PEM-encoded Ed25519 **public** key. |
| `DONATE_HIDE_PUBLIC_KEY`     | Alternatively, the PEM string itself (e.g. for env or secrets). |

The public key is not sensitive and can be committed or stored in normal config. Code generation uses the private key and is done outside the server (see internal documentation).

**Example (path to file):**

```bash
DONATE_HIDE_PUBLIC_KEY_FILE=/etc/timetracker/donate_hide_public.pem
```

### Option B: Shared secret (HMAC)

The server holds a secret; the code is derived from that secret and the system ID. Use this if you prefer a single shared secret instead of a key pair.

| Variable | Description |
|----------|-------------|
| `DONATE_HIDE_UNLOCK_SECRET`      | The secret string. Prefer not putting this in `.env` if the file is accessible to others. |
| `DONATE_HIDE_UNLOCK_SECRET_FILE` | Path to a file whose **first line** is the secret. Restrict file permissions (e.g. `chmod 600`). |

**Example (secret in a file):**

```bash
DONATE_HIDE_UNLOCK_SECRET_FILE=/run/secrets/donate_hide_secret
```

If both Option A and Option B are configured, the app uses the public key first; HMAC is used only when no public key is set.

## Enabling the feature

1. Choose Option A (public key) or Option B (secret).
2. Set the corresponding environment variable(s) for your deployment (e.g. in `.env`, Docker Compose, or your process manager).
3. Restart the application.

If neither is set, the feature is disabled: no code will be accepted and the Support visibility section still appears in Settings, but verification will always fail until you configure one of the options.

## Issuing codes to users

Codes are **per installation**: each instance has its own System ID, and a valid code for one instance is not valid for another.

- Users send you the **System ID** shown in their Settings → Support visibility.
- You generate the code for that System ID using the procedure and tools described in **internal documentation**. The code-generation script, key-generation steps, and private key handling are not in the public repository; maintainers use a separate, non-committed guide and script.
- You send the code to the user; they enter it in Settings and click Verify.

## User experience

- **Before verification:** Donate/support links and the support banner are visible (unless the user previously verified a code on this account).
- **After verification:** Donate and support UI is hidden for that user. The setting is stored per user and persists across sessions.

## Security notes

- With **Option A**, the server never has access to the private key, so compromise of the server does not allow forging new codes.
- With **Option B**, keep the secret out of version control and limit read access to the secret (or its file) to the process that runs the app.
- Codes are verified in constant time to reduce timing side channels.
