# Backup and full archive restore

This guide describes **full system backups** (ZIP archives with PostgreSQL `pg_dump` / SQLite file, settings snapshot, and static uploads) created from **Admin → Backups** or the `flask backup_create` CLI command, and how **restore** behaves in production-like deployments (including Docker).

## Creating backups

- **Web UI**: Admin → Backups → Create backup (downloads a `.zip` archive).
- **CLI** (inside the app container or venv with app context):

  ```bash
  flask backup_create
  ```

Archive layout is implemented in `app/utils/backup.py` (`create_backup`). The manifest lists database type and Alembic revision at backup time.

## Restoring a backup

Paths that run the same restore pipeline:

- **Admin → Backups → Restore** (upload or pick an existing archive; restore may run in a **background thread** so the browser can poll progress).
- **Import/Export → Restore** with a **ZIP** full-system archive (same `restore_backup` implementation as admin).
- **CLI**:

  ```bash
  flask backup_restore /path/to/backup_YYYYMMDD_HHMMSS.zip
  ```

Restore steps (see `restore_backup` in `app/utils/backup.py`):

1. Extract the ZIP to a temporary directory.
2. Close and dispose SQLAlchemy connections for the **current worker** (best-effort).
3. Replace the database: **PostgreSQL** uses `pg_restore --clean --if-exists` against the configured database; **SQLite** replaces the database file (with a timestamped safety copy when possible).
4. Merge `uploads/` from the archive into the app static uploads tree.
5. Run **Alembic migrations to head** (`flask db upgrade` equivalent) so the restored data matches the running application version.

## Behaviour during restore (important)

### Schema is replaced while the app keeps running

`pg_restore --clean` drops and recreates objects. Until the restore and migrations finish, the database can be **empty or inconsistent**. Any HTTP request that hits the database may see errors (for example `relation "users" does not exist` or `current transaction is aborted`).

The application sets an internal flag **`_database_restore_in_progress`** on the Flask app object for the duration of `restore_backup` (from archive extract through migrations). Code that must stay safe—such as the **client portal** template context processor—uses `is_database_restore_in_progress()` to **skip non-essential database reads** during that window.

### Single worker, concurrent greenlets

Typical Docker images start Gunicorn with **one worker** and an async worker class (for example Eventlet). Restore may run in a **background thread** while **other requests on the same worker** are still served. The in-progress flag reduces failures for global template injection; it does **not** guarantee that every route or API call will succeed mid-restore.

**Operational recommendation**: treat restore like maintenance—have users log out or pause use, perform restore in a quiet window, or temporarily stop routing traffic to the app (for example maintenance mode at the reverse proxy) if you need a hard guarantee.

### Multi-process deployments

The restore flag is **per process**. If you run **multiple Gunicorn workers or multiple app containers**, only the process executing `restore_backup` sets the flag. Other processes can still serve traffic against a database being rewritten. For multi-replica setups, coordinate maintenance (scale to one replica, or stop traffic) before restore.

### Admin restore thread and Flask context

The admin UI starts restore in a daemon thread. Cleanup must not use `current_app` in that thread; it uses the **captured application instance** (for example `app_obj.logger`) so file cleanup and logging do not raise “working outside of application context”.

## Troubleshooting

| Symptom | Likely cause |
|--------|----------------|
| `pg_restore failed` in UI or CLI message | Wrong archive, wrong DB credentials, or PostgreSQL version mismatch. Read the stderr fragment returned with the error. |
| Errors mentioning missing `users` during restore | Concurrent requests while schema is being dropped/recreated; reduce traffic or retry after progress shows completion. |
| `Working outside of application context` in logs after restore | Should be resolved for admin restore cleanup; if it reappears, check any new `current_app` usage inside threads. |

## Related documentation

- [Database recovery and automatic cleanup](../DATABASE_RECOVERY.md) — corrupted or partial startup states (not the same as intentional full archive restore).
- [Import/Export guide](../IMPORT_EXPORT_GUIDE.md) — JSON export/import vs full ZIP restore from this app.
- [Docker Compose setup](configuration/DOCKER_COMPOSE_SETUP.md) — volumes and database service layout.
