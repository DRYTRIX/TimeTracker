"""
Shared HTTP session for outbound integration calls (retries, timeouts).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT: tuple = (5, 30)  # (connect, read) seconds
_DEFAULT_TIMEOUT = DEFAULT_TIMEOUT  # backwards-compatible alias

_shared_session: Optional[requests.Session] = None


def integration_session(
    total_retries: int = 3,
    backoff_factor: float = 0.5,
    timeout: tuple = DEFAULT_TIMEOUT,
) -> requests.Session:
    """
    Session with retry on 429, 500, 502, 503, 504 for GET/POST/PUT/PATCH/DELETE.
    """
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def get_shared_session() -> requests.Session:
    """Lazy singleton session for integrations that do not manage their own."""
    global _shared_session
    if _shared_session is None:
        _shared_session = integration_session()
    return _shared_session


def session_request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Any = None,
    data: Any = None,
    timeout: Optional[Union[tuple, float, int]] = None,
    allow_redirects: bool = True,
    **kwargs: Any,
) -> requests.Response:
    """Perform request using session's default timeout; records Prometheus metrics."""
    from time import perf_counter

    from app.utils.hardening_metrics import host_from_url, observe_outbound_http

    to = timeout if timeout is not None else getattr(session, "request_timeout", DEFAULT_TIMEOUT)
    host = host_from_url(url)
    start = perf_counter()
    outcome = "error"
    try:
        response = session.request(
            method.upper(),
            url,
            headers=headers,
            params=params,
            json=json,
            data=data,
            timeout=to,
            allow_redirects=allow_redirects,
            **kwargs,
        )
        outcome = "ok" if response.status_code < 500 else "http_error"
        return response
    except Exception:
        outcome = "error"
        raise
    finally:
        observe_outbound_http(host, outcome, perf_counter() - start)


def request(
    method: str,
    url: str,
    *,
    timeout: Optional[Union[tuple, float, int]] = None,
    **kwargs: Any,
) -> requests.Response:
    """Module-level request helper with default timeout + retries."""
    return session_request(get_shared_session(), method, url, timeout=timeout, **kwargs)


def get(url: str, **kwargs: Any) -> requests.Response:
    return request("GET", url, **kwargs)


def post(url: str, **kwargs: Any) -> requests.Response:
    return request("POST", url, **kwargs)


def put(url: str, **kwargs: Any) -> requests.Response:
    return request("PUT", url, **kwargs)


def patch(url: str, **kwargs: Any) -> requests.Response:
    return request("PATCH", url, **kwargs)


def delete(url: str, **kwargs: Any) -> requests.Response:
    return request("DELETE", url, **kwargs)
