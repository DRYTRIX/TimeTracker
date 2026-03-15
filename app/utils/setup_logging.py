"""
Application logging setup.
Extracted from app/__init__.py for clearer separation of concerns.
"""

import logging
import os

from flask import Flask


def setup_logging(app: Flask) -> None:
    """Setup application logging including JSON logging."""
    from pythonjsonlogger import jsonlogger

    log_level = os.getenv("LOG_LEVEL", "INFO")
    default_log_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "timetracker.log")
    )
    log_file = os.getenv("LOG_FILE", default_log_path)

    json_log_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "app.jsonl")
    )

    handlers = [logging.StreamHandler()]

    try:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        handlers.append(file_handler)
    except (PermissionError, OSError) as e:
        print(f"Warning: Could not create log file '{log_file}': {e}")
        print("Logging to console only")

    for handler in handlers:
        handler.setLevel(getattr(logging, log_level.upper()))
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"))

    app.logger.handlers.clear()
    app.logger.propagate = False
    app.logger.setLevel(getattr(logging, log_level.upper()))
    for handler in handlers:
        app.logger.addHandler(handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.handlers = []
    for handler in handlers:
        root_logger.addHandler(handler)

    try:
        json_log_dir = os.path.dirname(json_log_path)
        if json_log_dir and not os.path.exists(json_log_dir):
            os.makedirs(json_log_dir, exist_ok=True)

        from logging.handlers import RotatingFileHandler as _RotatingFileHandler

        json_handler = _RotatingFileHandler(json_log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        json_formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        json_handler.setFormatter(json_formatter)
        json_handler.setLevel(logging.INFO)

        json_logger = logging.getLogger("timetracker")
        json_logger.handlers.clear()
        json_logger.addHandler(json_handler)
        json_logger.propagate = False

        app.logger.info("JSON logging initialized: %s", json_log_path)
    except (PermissionError, OSError) as e:
        app.logger.warning("Could not initialize JSON logging: %s", e)

    if not app.debug:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
