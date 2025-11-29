"""
Environment variable validation on startup.
Ensures required configuration is present and valid.
"""

import os
from typing import Dict, List, Tuple, Optional
from flask import current_app


class EnvValidationError(Exception):
    """Raised when environment validation fails"""

    pass


def validate_required_env_vars(required_vars: List[str], raise_on_error: bool = True) -> Tuple[bool, List[str]]:
    """
    Validate that required environment variables are set.

    Args:
        required_vars: List of required environment variable names
        raise_on_error: If True, raise EnvValidationError on failure

    Returns:
        Tuple of (is_valid, missing_vars)
    """
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing.append(var)

    if missing and raise_on_error:
        raise EnvValidationError(f"Missing required environment variables: {', '.join(missing)}")

    return len(missing) == 0, missing


def validate_secret_key() -> bool:
    """
    Validate that SECRET_KEY is set and secure.

    Returns:
        True if valid, False otherwise
    """
    secret_key = os.getenv("SECRET_KEY", "")
    placeholder_values = {"dev-secret-key-change-in-production", "your-secret-key-change-this", "your-secret-key-here"}

    if not secret_key:
        return False

    if secret_key in placeholder_values:
        return False

    if len(secret_key) < 32:
        return False

    return True


def validate_database_url() -> bool:
    """
    Validate that DATABASE_URL is set and valid.

    Returns:
        True if valid, False otherwise
    """
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url:
        # Check for PostgreSQL env vars
        if all([os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_USER"), os.getenv("POSTGRES_PASSWORD")]):
            return True
        return False

    # Basic validation - check for known database schemes
    valid_schemes = ["postgresql", "postgresql+psycopg2", "sqlite"]
    if not any(database_url.startswith(scheme) for scheme in valid_schemes):
        return False

    return True


def validate_production_config() -> Tuple[bool, List[str]]:
    """
    Validate production configuration requirements.

    Returns:
        Tuple of (is_valid, issues)
    """
    issues = []

    # Check SECRET_KEY
    if not validate_secret_key():
        issues.append("SECRET_KEY must be set and at least 32 characters long")

    # Check database
    if not validate_database_url():
        issues.append("DATABASE_URL or PostgreSQL environment variables must be set")

    # Check HTTPS settings in production
    flask_env = os.getenv("FLASK_ENV", "production")
    if flask_env == "production":
        session_secure = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
        if not session_secure:
            issues.append("SESSION_COOKIE_SECURE should be true in production")

    return len(issues) == 0, issues


def validate_optional_env_vars() -> Dict[str, bool]:
    """
    Validate optional environment variables and return their status.

    Returns:
        Dict mapping env var names to their validation status
    """
    optional_vars = {
        "TZ": lambda v: bool(v),
        "CURRENCY": lambda v: bool(v),
        "OIDC_ISSUER": lambda v: bool(v) if os.getenv("AUTH_METHOD", "").lower() in ("oidc", "both") else True,
        "OIDC_CLIENT_ID": lambda v: bool(v) if os.getenv("AUTH_METHOD", "").lower() in ("oidc", "both") else True,
        "OIDC_CLIENT_SECRET": lambda v: bool(v) if os.getenv("AUTH_METHOD", "").lower() in ("oidc", "both") else True,
    }

    results = {}
    for var, validator in optional_vars.items():
        value = os.getenv(var, "")
        results[var] = validator(value)

    return results


def validate_all(raise_on_error: bool = False) -> Tuple[bool, Dict[str, any]]:
    """
    Validate all environment configuration.

    Args:
        raise_on_error: If True, raise EnvValidationError on critical failures

    Returns:
        Tuple of (is_valid, validation_results)
    """
    results = {"required": {}, "optional": {}, "production": {}, "warnings": []}

    # Required vars (minimal set)
    required_vars = []  # Most vars have defaults, but SECRET_KEY is critical in production
    is_production = os.getenv("FLASK_ENV", "production") == "production"

    if is_production:
        required_vars = ["SECRET_KEY"]

    is_valid, missing = validate_required_env_vars(required_vars, raise_on_error=False)
    results["required"] = {"valid": is_valid, "missing": missing}

    # Secret key validation
    secret_valid = validate_secret_key()
    if not secret_valid and is_production:
        results["warnings"].append("SECRET_KEY is not secure for production")

    # Database validation
    db_valid = validate_database_url()
    results["required"]["database_valid"] = db_valid

    # Production config validation
    prod_valid, prod_issues = validate_production_config()
    results["production"] = {"valid": prod_valid, "issues": prod_issues}

    # Optional vars
    results["optional"] = validate_optional_env_vars()

    # Overall validity
    overall_valid = is_valid and db_valid and (not is_production or prod_valid)

    if not overall_valid and raise_on_error:
        error_msg = "Environment validation failed:\n"
        if missing:
            error_msg += f"  Missing: {', '.join(missing)}\n"
        if not db_valid:
            error_msg += "  Database configuration invalid\n"
        if prod_issues:
            error_msg += f"  Production issues: {', '.join(prod_issues)}\n"
        raise EnvValidationError(error_msg.strip())

    return overall_valid, results
