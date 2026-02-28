"""
OIDC Metadata Fetcher Utility

Provides functions to fetch OIDC discovery documents with retry logic
and better DNS handling to work around Python urllib3 DNS resolution issues.

Enhanced with multiple DNS resolution strategies, IP caching, connection pooling,
and Docker network detection for improved reliability.
"""

import socket
import time
import logging
import os
import threading
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Thread-safe IP address cache with TTL
class IPCache:
    """Thread-safe cache for DNS resolution results with TTL"""
    
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Tuple[str, datetime]] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
    
    def get(self, hostname: str) -> Optional[str]:
        """Get cached IP address if valid"""
        with self._lock:
            if hostname in self._cache:
                ip, expiry = self._cache[hostname]
                if datetime.now() < expiry:
                    logger.debug("IP cache hit for %s: %s", hostname, self._mask_ip(ip))
                    return ip
                else:
                    # Expired, remove it
                    del self._cache[hostname]
            return None
    
    def set(self, hostname: str, ip: str, ttl: Optional[int] = None):
        """Cache IP address with TTL"""
        ttl = ttl or self.default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        with self._lock:
            self._cache[hostname] = (ip, expiry)
            logger.debug("IP cached for %s: %s (TTL: %ds)", hostname, self._mask_ip(ip), ttl)
    
    def clear(self, hostname: Optional[str] = None):
        """Clear cache entry or entire cache"""
        with self._lock:
            if hostname:
                self._cache.pop(hostname, None)
            else:
                self._cache.clear()
    
    def _mask_ip(self, ip: str) -> str:
        """Mask IP address for logging (show only first octet)"""
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.xxx.xxx.xxx"
        return ip

# Global IP cache instance (will be initialized with config TTL in create_app)
# Default to a cache with default TTL to avoid None errors
_ip_cache = IPCache(default_ttl=300)


def initialize_ip_cache(ttl: int = 300):
    """Initialize the global IP cache with a specific TTL"""
    global _ip_cache
    _ip_cache = IPCache(default_ttl=ttl)
    logger.info("IP cache initialized with TTL: %d seconds", ttl)


def detect_docker_environment() -> bool:
    """
    Detect if running in Docker environment.
    
    Returns:
        True if running in Docker, False otherwise
    """
    # Check for Docker-specific files
    docker_indicators = [
        '/.dockerenv',
        '/proc/self/cgroup',
    ]
    
    for indicator in docker_indicators:
        if os.path.exists(indicator):
            # Additional check for cgroup
            if indicator == '/proc/self/cgroup':
                try:
                    with open('/proc/self/cgroup', 'r') as f:
                        content = f.read()
                        if 'docker' in content or 'containerd' in content:
                            return True
                except Exception:
                    pass
            else:
                return True
    
    # Check for Docker environment variables
    if os.getenv('DOCKER_CONTAINER') or os.getenv('container') == 'docker':
        return True
    
    return False


def resolve_hostname_socket(hostname: str, timeout: int = 5) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Resolve hostname using socket.gethostbyname().
    
    Args:
        hostname: The hostname to resolve
        timeout: DNS resolution timeout in seconds
        
    Returns:
        Tuple of (success: bool, ip_address: Optional[str], error_message: Optional[str])
    """
    try:
        # Set socket timeout
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            ip_address = socket.gethostbyname(hostname)
            logger.debug("Socket DNS resolution successful for %s: %s", hostname, _ip_cache._mask_ip(ip_address))
            return True, ip_address, None
        finally:
            socket.setdefaulttimeout(old_timeout)
    except socket.gaierror as e:
        error_msg = f"Socket DNS resolution failed for {hostname}: {str(e)}"
        logger.debug(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during socket DNS resolution for {hostname}: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg


def resolve_hostname_getaddrinfo(hostname: str, timeout: int = 5) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Resolve hostname using socket.getaddrinfo() for more robust resolution.
    
    Args:
        hostname: The hostname to resolve
        timeout: DNS resolution timeout in seconds
        
    Returns:
        Tuple of (success: bool, ip_address: Optional[str], error_message: Optional[str])
    """
    try:
        # Try IPv4 first
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            if addr_info:
                ip_address = addr_info[0][4][0]
                logger.debug("getaddrinfo DNS resolution successful for %s: %s", hostname, _ip_cache._mask_ip(ip_address))
                return True, ip_address, None
        finally:
            socket.setdefaulttimeout(old_timeout)
        
        return False, None, "No address found"
    except socket.gaierror as e:
        error_msg = f"getaddrinfo DNS resolution failed for {hostname}: {str(e)}"
        logger.debug(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during getaddrinfo DNS resolution for {hostname}: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg


def resolve_hostname_multiple_strategies(
    hostname: str,
    timeout: int = 5,
    strategy: str = "auto",
    use_cache: bool = True,
) -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Resolve hostname using multiple strategies.
    
    Args:
        hostname: The hostname to resolve
        timeout: DNS resolution timeout in seconds
        strategy: Resolution strategy - "auto", "socket", "getaddrinfo", or "both"
        use_cache: Whether to use IP cache
        
    Returns:
        Tuple of (success: bool, ip_address: Optional[str], error_message: Optional[str], strategy_used: str)
    """
    # Check cache first
    if use_cache:
        cached_ip = _ip_cache.get(hostname)
        if cached_ip:
            logger.debug("Using cached IP for %s", hostname)
            return True, cached_ip, None, "cache"
    
    strategies_to_try = []
    
    if strategy == "auto" or strategy == "both":
        # Try socket first (usually faster), then getaddrinfo
        strategies_to_try = [
            ("socket", resolve_hostname_socket),
            ("getaddrinfo", resolve_hostname_getaddrinfo),
        ]
    elif strategy == "socket":
        strategies_to_try = [("socket", resolve_hostname_socket)]
    elif strategy == "getaddrinfo":
        strategies_to_try = [("getaddrinfo", resolve_hostname_getaddrinfo)]
    else:
        # Default to socket
        strategies_to_try = [("socket", resolve_hostname_socket)]
    
    last_error = None
    for strategy_name, resolver_func in strategies_to_try:
        success, ip_address, error = resolver_func(hostname, timeout)
        if success and ip_address:
            # Cache the result
            if use_cache:
                _ip_cache.set(hostname, ip_address)
            logger.info("DNS resolution successful for %s using %s strategy: %s", hostname, strategy_name, _ip_cache._mask_ip(ip_address))
            return True, ip_address, None, strategy_name
        last_error = error
    
    logger.warning("All DNS resolution strategies failed for %s. Last error: %s", hostname, last_error)
    return False, None, last_error or "All resolution strategies failed", "none"


def create_optimized_session(timeout: int = 10) -> requests.Session:
    """
    Create a requests session with optimized connection pooling and retry strategy.
    
    Args:
        timeout: Default timeout for requests
        
    Returns:
        Configured requests.Session
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "OPTIONS"],
    )
    
    # Configure HTTP adapter with connection pooling
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
        pool_block=False,
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default timeout
    session.timeout = timeout
    
    return session


def test_dns_resolution(hostname: str, timeout: int = 5, strategy: str = "auto") -> Tuple[bool, Optional[str], Optional[str], str]:
    """
    Test DNS resolution for a hostname using multiple strategies.
    
    Args:
        hostname: The hostname to resolve
        timeout: DNS resolution timeout in seconds
        strategy: Resolution strategy - "auto", "socket", "getaddrinfo", or "both"
        
    Returns:
        Tuple of (success: bool, ip_address: Optional[str], error_message: Optional[str], strategy_used: str)
    """
    return resolve_hostname_multiple_strategies(hostname, timeout, strategy, use_cache=True)


def try_docker_internal_name(hostname: str, issuer_url: str) -> Optional[str]:
    """
    Try to construct a Docker internal service name URL if in Docker environment.
    
    This attempts common Docker service name patterns based on the hostname.
    
    Args:
        hostname: The original hostname
        issuer_url: The original issuer URL
        
    Returns:
        Modified issuer URL using Docker internal name, or None if not applicable
    """
    if not detect_docker_environment():
        return None
    
    # Common patterns: auth.example.com -> auth, auth.goat-lovers.xxx -> authentik
    # Try extracting the first part of the hostname as potential service name
    service_name = hostname.split('.')[0]
    
    # Common service name mappings
    service_mappings = {
        'auth': 'authentik',
        'idp': 'authentik',
        'keycloak': 'keycloak',
        'authelia': 'authelia',
    }
    
    # Check if we have a mapping
    if service_name.lower() in service_mappings:
        service_name = service_mappings[service_name.lower()]
    
    # Try common ports
    parsed = urlparse(issuer_url)
    scheme = parsed.scheme
    port = parsed.port
    
    # Default ports based on scheme
    if not port:
        port = 9443 if scheme == 'https' else 9000
    
    # Construct internal URL
    internal_url = f"{scheme}://{service_name}:{port}"
    if parsed.path:
        internal_url += parsed.path
    
    logger.info("Attempting Docker internal URL: %s (original: %s)", internal_url, issuer_url)
    return internal_url


def classify_error(error: Exception) -> str:
    """
    Classify error type for intelligent retry logic.
    
    Args:
        error: The exception to classify
        
    Returns:
        Error type: "dns", "network", "http", "ssl", "timeout", or "unknown"
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # DNS resolution errors
    if isinstance(error, requests.exceptions.ConnectionError):
        if any(indicator in error_str for indicator in ["nameresolutionerror", "failed to resolve", "[errno -2]", "name or service not known"]):
            return "dns"
        return "network"
    
    # Timeout errors
    if isinstance(error, (requests.exceptions.Timeout, socket.timeout)):
        return "timeout"
    
    # HTTP errors
    if isinstance(error, requests.exceptions.HTTPError):
        return "http"
    
    # SSL/TLS errors
    if isinstance(error, requests.exceptions.SSLError) or "ssl" in error_str or "certificate" in error_str:
        return "ssl"
    
    # Network connectivity errors
    if isinstance(error, (requests.exceptions.ConnectionError, socket.error)):
        return "network"
    
    return "unknown"


def fetch_oidc_metadata(
    issuer_url: str,
    max_retries: int = 3,
    retry_delay: int = 2,
    timeout: int = 10,
    use_dns_test: bool = True,
    dns_strategy: str = "auto",
    use_ip_directly: bool = True,
    use_docker_internal: bool = True,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    """
    Fetch OIDC metadata from the discovery endpoint with enhanced DNS handling.
    
    This function uses multiple DNS resolution strategies and connection pooling
    to work around Python urllib3 DNS resolution issues.
    
    Args:
        issuer_url: The OIDC issuer URL (e.g., https://auth.example.com)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 2)
        timeout: Request timeout in seconds (default: 10)
        use_dns_test: Whether to test DNS resolution first (default: True)
        dns_strategy: DNS resolution strategy - "auto", "socket", "getaddrinfo", or "both"
        use_ip_directly: Use IP address directly for HTTP issuer URLs when DNS resolution
            succeeds (default: True). For HTTPS, the request is always made to the original
            issuer hostname to satisfy TLS SNI and virtual hosting requirements.
        use_docker_internal: Try Docker internal names if external DNS fails (default: True)
        
    Returns:
        Tuple of (metadata_dict: Optional[Dict], error_message: Optional[str], diagnostics: Optional[Dict])
        Returns (None, error_message, diagnostics) on failure, (metadata, None, diagnostics) on success
    """
    diagnostics = {
        "dns_resolution": {},
        "strategies_tried": [],
        "connection_pool_stats": {},
    }
    
    # Parse the issuer URL
    try:
        parsed = urlparse(issuer_url)
        if not parsed.scheme or not parsed.netloc:
            return None, f"Invalid issuer URL format: {issuer_url}", diagnostics
        
        hostname = parsed.netloc.split(":")[0]
        original_metadata_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
        metadata_url = original_metadata_url
    except Exception as e:
        return None, f"Failed to parse issuer URL: {str(e)}", diagnostics
    
    # Test DNS resolution first if requested
    resolved_ip = None
    dns_strategy_used = "none"
    if use_dns_test:
        dns_success, resolved_ip, dns_error, dns_strategy_used = resolve_hostname_multiple_strategies(
            hostname, timeout, dns_strategy, use_cache=True
        )
        diagnostics["dns_resolution"] = {
            "success": dns_success,
            "ip_address": _ip_cache._mask_ip(resolved_ip) if resolved_ip else None,
            "strategy": dns_strategy_used,
            "error": dns_error,
        }
        
        if dns_success and resolved_ip and use_ip_directly and parsed.scheme == "http":
            # Replace hostname with IP in URL (HTTP only).
            # For HTTPS, we always use the original issuer hostname - using the IP breaks
            # TLS SNI and virtual hosting (IDPs typically require the domain in SNI/Host).
            metadata_url = original_metadata_url.replace(hostname, resolved_ip)
            logger.info("Using IP address directly for metadata fetch: %s -> %s", hostname, _ip_cache._mask_ip(resolved_ip))
        elif not dns_success:
            logger.warning(
                "DNS resolution test failed for %s using %s strategy, but will attempt metadata fetch anyway",
                hostname,
                dns_strategy_used,
            )
    
    # Create optimized session
    session = create_optimized_session(timeout)
    
    # Attempt to fetch metadata with retry logic
    last_error = None
    last_error_type = None
    docker_internal_tried = False
    
    for attempt in range(1, max_retries + 1):
        current_url = metadata_url
        diagnostics["strategies_tried"].append({
            "attempt": attempt,
            "url": current_url,
            "strategy": dns_strategy_used,
        })
        
        try:
            logger.info(
                "Fetching OIDC metadata from %s (attempt %d/%d, strategy: %s)",
                current_url,
                attempt,
                max_retries,
                dns_strategy_used,
            )
            
            # Prepare headers - include Host header for HTTPS with IP
            headers = {}
            if parsed.scheme == "https" and resolved_ip and use_ip_directly:
                headers["Host"] = hostname
            
            response = session.get(current_url, timeout=timeout, headers=headers)
            response.raise_for_status()
            
            metadata = response.json()
            
            # Validate that we got a proper OIDC discovery document
            if not isinstance(metadata, dict):
                raise ValueError("Metadata response is not a JSON object")
            
            required_fields = ["issuer", "authorization_endpoint", "token_endpoint"]
            missing_fields = [field for field in required_fields if field not in metadata]
            if missing_fields:
                raise ValueError(
                    f"Missing required fields in metadata: {', '.join(missing_fields)}"
                )
            
            # Log connection pool stats
            if hasattr(session, 'get_adapter'):
                adapter = session.get_adapter(current_url)
                if hasattr(adapter, 'poolmanager'):
                    pool = adapter.poolmanager.connection_from_url(current_url)
                    diagnostics["connection_pool_stats"] = {
                        "num_connections": getattr(pool, 'num_connections', 'unknown'),
                        "num_pools": getattr(pool, 'num_pools', 'unknown'),
                    }
            
            logger.info(
                "Successfully fetched OIDC metadata from %s (issuer: %s, strategy: %s)",
                current_url,
                metadata.get("issuer"),
                dns_strategy_used,
            )
            return metadata, None, diagnostics
            
        except requests.exceptions.Timeout as e:
            last_error_type = "timeout"
            last_error = f"Timeout fetching metadata from {current_url}: {str(e)}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, max_retries)
            
        except requests.exceptions.ConnectionError as e:
            error_type = classify_error(e)
            last_error_type = error_type
            error_str = str(e)
            
            if error_type == "dns":
                last_error = (
                    f"DNS resolution failed for {hostname}: {error_str}. "
                    "This may occur when Python's DNS resolver cannot resolve the domain. "
                    "Try configuring DNS servers in Docker or using container names for internal services."
                )
                # Try Docker internal name if not already tried
                if use_docker_internal and not docker_internal_tried and detect_docker_environment():
                    docker_url = try_docker_internal_name(hostname, issuer_url)
                    if docker_url:
                        docker_internal_tried = True
                        logger.info("Attempting Docker internal URL after DNS failure")
                        # Update metadata_url and continue to next attempt
                        metadata_url = f"{docker_url.rstrip('/')}/.well-known/openid-configuration"
                        diagnostics["strategies_tried"][-1]["docker_internal_url"] = docker_url
                        continue
            else:
                last_error = f"Connection error fetching metadata from {current_url}: {error_str}"
            logger.warning("%s (attempt %d/%d, error_type: %s)", last_error, attempt, max_retries, error_type)
            
        except requests.exceptions.HTTPError as e:
            last_error_type = "http"
            last_error = f"HTTP error fetching metadata from {current_url}: {str(e)}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, max_retries)
            # Don't retry on HTTP errors (4xx, 5xx) - they're unlikely to resolve
            break
            
        except requests.exceptions.SSLError as e:
            last_error_type = "ssl"
            last_error = f"SSL/TLS error fetching metadata from {current_url}: {str(e)}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, max_retries)
            # SSL errors usually don't resolve with retries
            break
            
        except ValueError as e:
            last_error_type = "validation"
            last_error = f"Invalid metadata response from {current_url}: {str(e)}"
            logger.error("%s (attempt %d/%d)", last_error, attempt, max_retries)
            # Don't retry on validation errors
            break
            
        except Exception as e:
            last_error_type = "unknown"
            last_error = f"Unexpected error fetching metadata from {current_url}: {str(e)}"
            logger.error("%s (attempt %d/%d)", last_error, attempt, max_retries)
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries:
            delay = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
            logger.info("Waiting %d seconds before retry...", delay)
            time.sleep(delay)
    
    # All retries failed
    diagnostics["last_error_type"] = last_error_type
    error_message = (
        f"Failed to fetch OIDC metadata after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
    logger.error(error_message)
    return None, error_message, diagnostics
