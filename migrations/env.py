from __future__ import with_statement

import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
import sqlalchemy as sa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.metadata
config.set_main_option(
    'sqlalchemy.url',
    str(current_app.extensions['migrate'].db.get_engine().url).replace(
        '%', '%%'))
target_metadata = current_app.extensions['migrate'].db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    def _ensure_alembic_version_can_store_long_revision_ids(connection, min_len: int = 255) -> None:
        """
        Ensure alembic_version.version_num is wide enough for long revision ids.

        Some older PostgreSQL installs created alembic_version.version_num as VARCHAR(32),
        but we use descriptive revision ids longer than that. If the column is too small,
        Alembic can fail while updating the version table (even if the actual migration
        itself succeeds).
        """
        try:
            if connection.dialect.name != "postgresql":
                return

            inspector = sa.inspect(connection)
            if "alembic_version" not in inspector.get_table_names():
                return

            # Prefer information_schema, which is reliable across SQLAlchemy versions.
            current_len = None
            try:
                res = connection.execute(
                    sa.text(
                        """
                        SELECT character_maximum_length
                        FROM information_schema.columns
                        WHERE table_name = 'alembic_version'
                          AND column_name = 'version_num'
                        """
                    )
                ).scalar()
                if isinstance(res, int):
                    current_len = res
            except Exception:
                current_len = None

            if current_len is not None and current_len >= min_len:
                return

            connection.execute(
                sa.text(
                    f"ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR({min_len})"
                )
            )
            try:
                connection.commit()
            except Exception:
                # If we're already in a transaction, Alembic will commit/rollback later.
                pass

            if current_len is not None:
                logger.info(
                    f"Expanded alembic_version.version_num from {current_len} to {min_len}"
                )
            else:
                logger.info(
                    f"Ensured alembic_version.version_num is at least VARCHAR({min_len})"
                )
        except Exception as e:
            logger.warning(f"Could not expand alembic_version.version_num: {e}")

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    connectable = current_app.extensions['migrate'].db.get_engine()

    try:
        # CRITICAL FIX: Use connection that supports explicit commits for DDL
        # PostgreSQL requires explicit commits for DDL operations in some connection modes
        connection = connectable.connect()
        try:
            # Pre-flight fix: ensure alembic_version can store long revision ids
            _ensure_alembic_version_can_store_long_revision_ids(connection)

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                process_revision_directives=process_revision_directives,
                transaction_per_migration=False,  # Single transaction for all migrations
                **current_app.extensions['migrate'].configure_args
            )

            # Run migrations - context.begin_transaction() handles the transaction
            # But we need to ensure the connection itself commits
            with context.begin_transaction():
                context.run_migrations()
            
            # CRITICAL: Explicitly commit the connection transaction
            # context.begin_transaction() may commit its transaction, but the connection
            # transaction might still need explicit commit to persist to database
            if connection.in_transaction():
                logger.info("Connection still in transaction, explicitly committing...")
                connection.commit()
            else:
                logger.info("Connection transaction already committed/closed")
            
            # Verify commit worked by checking if tables exist
            try:
                from sqlalchemy import inspect
                inspector = inspect(connection)
                tables = inspector.get_table_names()
                logger.info(f"Post-migration verification: Found {len(tables)} tables in database")
                if 'alembic_version' in tables:
                    logger.info("✓ alembic_version table exists - migrations persisted successfully")
                else:
                    logger.error("✗ alembic_version table missing - migrations may not have persisted")
            except Exception as verify_error:
                logger.warning(f"Could not verify migration persistence: {verify_error}")
                
        finally:
            # Always close the connection
            connection.close()
                
    except Exception as e:
        # Log the full error with traceback for debugging
        import traceback
        logger.error(f"Migration failed with error: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        # Re-raise to ensure the migration command fails properly
        raise


try:
    # Use print() so it always appears in container logs.
    print(f"[alembic] offline_mode={context.is_offline_mode()}")
except Exception:
    pass

if context.is_offline_mode():
    try:
        logger.info("Alembic running in OFFLINE mode (no DB writes)")
    except Exception:
        pass
    try:
        run_migrations_offline()
    except Exception as e:
        import traceback
        logger.error(f"Migration failed (offline mode) with error: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise
else:
    try:
        logger.info("Alembic running in ONLINE mode (DB writes enabled)")
    except Exception:
        pass
    try:
        run_migrations_online()
    except Exception as e:
        import traceback
        logger.error(f"Migration failed (online mode) with error: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise
