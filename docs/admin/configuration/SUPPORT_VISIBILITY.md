# Support / Donate visibility

This guide describes how to configure the optional **Support visibility** feature. When enabled, an **admin** can hide donate and support prompts (sidebar link, header button, support banner, and donate widgets) **for all users** by entering a **code** that is issued per installation.

## What admins see

- In **Admin → Settings**, the **Support visibility** section shows the **System ID** (a stable UUID for your installation) and a field to enter a code.
- After a valid code is entered and **Verify and hide for everyone** is clicked, donate and support UI is hidden **system-wide** for all users.
- The System ID does not change between restarts; it identifies your instance so you can request the correct code.

## Server configuration

You can enable verification in two ways. Only one is required.

### Option A: Public key (recommended)

The server stores **only a public key**. The **private key** is never used by the application; you keep it only for running the code-generation script. This is the most secure option.

| Variable | Description |
|----------|-------------|
| `DONATE_HIDE_PUBLIC_KEY_FILE` | Path to a file containing the PEM-encoded Ed25519 **public** key. |
| `DONATE_HIDE_PUBLIC_KEY`     | Alternatively, the PEM string itself (e.g. for env or secrets). |

**Quick setup (when you already have the private key):**

1. **Derive the public key** from your private key (run once, on the same machine where you have the private key):
   ```bash
   openssl pkey -in donate_hide_private.pem -pubout -out donate_hide_public.pem
   ```
2. **On the server**, configure the **public** key only. For example in `.env` or your deployment config:
   ```bash
   DONATE_HIDE_PUBLIC_KEY_FILE=/path/to/donate_hide_public.pem
   ```
   Use a path where you deploy `donate_hide_public.pem` (not the private key). Alternatively set `DONATE_HIDE_PUBLIC_KEY` to the full PEM contents of the public key.
3. Restart the application. The app will use the public key to **verify** codes; it never needs or uses the private key.
4. When issuing codes, run the code-generation script **offline** with your **private** key (see internal documentation).

**Automatic detection:** If you do not set `DONATE_HIDE_PUBLIC_KEY` or `DONATE_HIDE_PUBLIC_KEY_FILE`, the app looks for a file named **`donate_hide_public.pem`** in the project root. Place it there for local runs; for Docker, place it in the build context root and the image sets `DONATE_HIDE_PUBLIC_KEY_FILE=/app/donate_hide_public.pem` so the copied file is used.

**GitHub Actions (release and development workflows):** To bake the public key into the Docker image when building via GitHub Actions, add a repository secret **`DONATE_HIDE_PUBLIC_KEY_PEM`** (Settings → Secrets and variables → Actions) with the **full PEM contents** of your public key (including `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----`). The workflow writes it to `donate_hide_public.pem` before the build so the image has the key at `/app/donate_hide_public.pem`. If the secret is not set, the image still builds; Support visibility verification will simply be disabled until you configure the key at runtime (e.g. via volume or env).

The public key file is not sensitive and can live in normal config. Never deploy or configure the private key on the server.

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

If neither is set, the feature is disabled: no code will be accepted and the Support visibility section still appears in Admin → Settings, but verification will always fail until you configure one of the options.

## Issuing codes

Codes are **per installation**: each instance has its own System ID, and a valid code for one instance is not valid for another.

- An admin copies the **System ID** from Admin → Settings → Support visibility (or you provide it from your deployment).
- You generate the code for that System ID using the procedure and tools described in **internal documentation**. The code-generation script, key-generation steps, and private key handling are not in the public repository; maintainers use a separate, non-committed guide and script.
- You send the code to the admin; they enter it in Admin → Settings and click **Verify and hide for everyone**.

## User experience

- **Before verification:** Donate/support links and the support banner are visible to all users.
- **After verification:** Donate and support UI is hidden **for everyone**. The setting is stored in system settings and persists across restarts.

## Security notes

- With **Option A**, the server never has access to the private key, so compromise of the server does not allow forging new codes.
- With **Option B**, keep the secret out of version control and limit read access to the secret (or its file) to the process that runs the app.
- Codes are verified in constant time to reduce timing side channels.
