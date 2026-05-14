# Uninstalling or Removing TimeTracker

This guide explains how to **stop** TimeTracker, **remove containers**, and optionally **delete all data** (database, uploads, logs). Always **back up** anything you need before destructive steps.

---

## Before you remove anything (backup)

### PostgreSQL (Docker Compose with bundled `db`)

From the directory where you run Compose:

```bash
docker compose exec db pg_dump -U timetracker timetracker > timetracker-backup.sql
```

Adjust `-U` and database name if you changed `POSTGRES_USER` / `POSTGRES_DB` in `.env`.

### Uploads and app data (named volumes)

Uploads and local app data often live in Docker volumes (e.g. `app_uploads`, `app_data`). To archive uploads from a named volume (example project name prefix `timetracker`):

```bash
docker run --rm -v timetracker_app_uploads:/data -v "$(pwd):/backup" alpine tar czf /backup/timetracker-uploads.tgz -C /data .
```

List volumes: `docker volume ls | grep -i timetracker`

### Revoke integrations (optional)

After shutdown, rotate or revoke **OAuth**, **SMTP**, **webhooks**, and **API tokens** you created for this instance. See [Documentation index](docs/README.md) and admin guides under `docs/admin/`.

---

## Disabling or removing the AI helper

Use this when you want **no LLM calls** from TimeTracker (web **AI Helper**, `POST /api/ai/chat`, or `POST /api/v1/ai/chat`) while optionally reclaiming disk from bundled Ollama. You do **not** need to uninstall the whole app.

### 1) Turn AI off in the application

1. **Admin UI:** **Admin → System Settings → AI Helper** — disable the AI helper and save (wording may vary slightly by version).
2. **Environment:** In `.env`, set `AI_ENABLED=false`. Remove or comment out values you no longer need, for example `AI_API_KEY`, `AI_BASE_URL`, or `AI_MODEL`, so a future misconfiguration does not re-enable calls by accident.
3. **Restart the app** so the container picks up env changes, for example:

   ```bash
   docker compose up -d
   ```

   For a non-Docker install, restart your `gunicorn` / `flask` process after editing the environment.

After this, the server should refuse AI requests (UI and API behave as “AI disabled”).

### 2) If you use the Docker Compose `ai` profile (bundled Ollama)

Bundled **Ollama** and **ollama-init** only run when you use `docker compose --profile ai ...`. Stopping AI in the app (step 1) is enough for security and behavior; the Ollama container may still run until you stop it.

- **Stop Ollama containers but keep volumes** (models stay on disk for a later reinstall):

  ```bash
  docker compose --profile ai down
  ```

  Then start the main stack **without** the profile so Ollama is not started again:

  ```bash
  docker compose up -d
  ```

- **Remove only the Ollama model cache** (typical volume name contains `ollama_data`; confirm with `docker volume ls`):

  ```bash
  docker volume ls | grep -i ollama
  docker volume rm <your_project>_ollama_data
  ```

  Replace `<your_project>_ollama_data` with the exact name from the list. This keeps your **PostgreSQL** and other project volumes if they use different names.

- **Remove all project volumes** (destroys DB, uploads, logs, **and** `ollama_data` — only if you intend full data removal):

  ```bash
  docker compose --profile ai down -v
  ```

- **Remove the Ollama image** if nothing else on the host needs it:

  ```bash
  docker rmi ollama/ollama:latest
  ```

If Ollama runs **on the host** (outside Compose), stop or uninstall that service separately; setting `AI_ENABLED=false` and clearing `AI_BASE_URL` / `AI_PROVIDER` in `.env` prevents the app from calling it.

### 3) API tokens and hosted provider keys

- **API tokens:** In **Admin → API tokens**, delete or rotate any token that includes scopes **`read:ai`** or **`write:ai`** if you no longer want programmatic AI access.
- **Hosted OpenAI-compatible providers:** Revoke or rotate the key at the provider’s dashboard. Remove `AI_API_KEY` from `.env` and from **System Settings** if it was saved there (especially when using **settings encryption** — see [README](README.md) *Encrypting stored secrets*).

### 4) Quick reference

| Goal | What to do |
|------|----------------|
| AI off, app keeps running | `AI_ENABLED=false` + restart app; disable in Admin if you use DB-backed settings |
| Stop bundled Ollama containers | `docker compose --profile ai down` then `docker compose up -d` without profile |
| Delete downloaded models only | `docker volume rm …ollama_data…` (see step 2) |
| Full stack + all compose volumes gone | `docker compose --profile ai down -v` |

For the default stack without AI, see the next section. For install and enable steps, see [INSTALLATION.md](INSTALLATION.md) and [README.md](README.md) (*AI Helper*).

---

## Docker Compose: default stack (HTTPS + Postgres, no AI profile)

Run from the repository root (or the directory containing your `docker-compose.yml`):

```bash
# Stop and remove containers (keeps named volumes — data remains)
docker compose down

# Stop and remove containers AND named volumes (deletes DB, app data, uploads, logs volume)
docker compose down -v
```

If you used the root `docker-compose.yml` with **nginx** and **certgen**, you may also remove generated certs under `nginx/ssl/` if you no longer need them.

Remove locally built images if desired:

```bash
docker images | grep -i timetracker
docker rmi <image_id>
```

---

## Docker Compose: with bundled Ollama (`--profile ai`)

If you started the stack with the optional AI profile, prefer the step-by-step table in **[Disabling or removing the AI helper](#disabling-or-removing-the-ai-helper)** so you can drop Ollama volumes **without** deleting the database by mistake.

Quick removal of **everything** defined in this compose project (containers and **all** named volumes, including Postgres data and `ollama_data`):

```bash
docker compose --profile ai down -v
```

Remove the Ollama image if you no longer need it:

```bash
docker rmi ollama/ollama:latest
```

---

## Published image stacks

### `docker-compose.example.yml` (HTTP on port 8080)

```bash
docker compose -f docker-compose.example.yml down -v
```

### `docker/docker-compose.remote.yml` (HTTPS + published image)

```bash
docker compose -f docker/docker-compose.remote.yml down -v
```

Adjust `-f` paths if your working directory is not the repository root.

---

## SQLite local test compose

```bash
docker compose -f docker/docker-compose.local-test.yml down -v
```

---

## Pip / local development (no Docker)

1. Stop the app (Ctrl+C or stop the `flask` / `gunicorn` process).
2. Remove the virtual environment directory you created (e.g. `rm -rf .venv`).
3. Delete the SQLite file if you used one (path from your `DATABASE_URL` or `pytest_*.sqlite` for tests).
4. Remove the cloned repository if you no longer need the code: `cd .. && rm -rf TimeTracker`.

If you used `make` targets, see [Makefile](Makefile) for any `clean` target available in your checkout.

---

## Render (managed hosting)

Remove or suspend the **Web Service** (and any **PostgreSQL** add-on) from the Render dashboard. See [docs/deploy/RENDER.md](docs/deploy/RENDER.md) for how the service was defined (`render.yaml`).

---

## Summary

| Goal | Command pattern |
|------|------------------|
| Stop only | `docker compose down` |
| Remove containers + volumes | `docker compose down -v` |
| AI off + Ollama stopped (see AI section) | [Disabling or removing the AI helper](#disabling-or-removing-the-ai-helper) |
| AI profile + **all** project volumes | `docker compose --profile ai down -v` |

For **install** and **optional AI**, see [INSTALLATION.md](INSTALLATION.md) and [README.md](README.md).
