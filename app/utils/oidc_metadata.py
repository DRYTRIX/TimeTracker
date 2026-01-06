"""
OIDC Metadata Fetcher Utility

Provides functions to fetch OIDC discovery documents with retry logic
and better DNS handling to work around Python urllib3 DNS resolution issues.
"""

import socket
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


def test_dns_resolution(hostname: str, timeout: int = 5) -> tuple[bool, Optional[str]]:
    """
    Test DNS resolution for a hostname using Python's socket library.
    
    Args:
        hostname: The hostname to resolve
        timeout: DNS resolution timeout in seconds
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        # Use socket.gethostbyname which may work better than urllib3's resolver
        ip_address = socket.gethostbyname(hostname)
        logger.debug("DNS resolution successful for %s: %s", hostname, ip_address)
        return True, None
    except socket.gaierror as e:
        error_msg = f"DNS resolution failed for {hostname}: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during DNS resolution for {hostname}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def fetch_oidc_metadata(
    issuer_url: str,
    max_retries: int = 3,
    retry_delay: int = 2,
    timeout: int = 10,
    use_dns_test: bool = True,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch OIDC metadata from the discovery endpoint with retry logic.
    
    This function uses the requests library which may have better DNS handling
    than urllib3 used by Authlib. It also implements exponential backoff retry.
    
    Args:
        issuer_url: The OIDC issuer URL (e.g., https://auth.example.com)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 2)
        timeout: Request timeout in seconds (default: 10)
        use_dns_test: Whether to test DNS resolution first (default: True)
        
    Returns:
        Tuple of (metadata_dict: Optional[Dict], error_message: Optional[str])
        Returns (None, error_message) on failure, (metadata, None) on success
    """
    # Parse the issuer URL
    try:
        parsed = urlparse(issuer_url)
        if not parsed.scheme or not parsed.netloc:
            return None, f"Invalid issuer URL format: {issuer_url}"
        
        hostname = parsed.netloc.split(":")[0]
        metadata_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
    except Exception as e:
        return None, f"Failed to parse issuer URL: {str(e)}"
    
    # Test DNS resolution first if requested
    if use_dns_test:
        dns_success, dns_error = test_dns_resolution(hostname, timeout=timeout)
        if not dns_success:
            logger.warning(
                "DNS resolution test failed for %s, but will attempt metadata fetch anyway",
                hostname,
            )
            # Continue anyway - sometimes requests library works even if socket doesn't
    
    # Attempt to fetch metadata with retry logic
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Fetching OIDC metadata from %s (attempt %d/%d)",
                metadata_url,
                attempt,
                max_retries,
            )
            
            response = requests.get(metadata_url, timeout=timeout)
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
            
            logger.info(
                "Successfully fetched OIDC metadata from %s (issuer: %s)",
                metadata_url,
                metadata.get("issuer"),
            )
            return metadata, None
            
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout fetching metadata from {metadata_url}: {str(e)}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, max_retries)
            
        except requests.exceptions.ConnectionError as e:
            # This often includes DNS resolution errors
            error_str = str(e)
            if "NameResolutionError" in error_str or "Failed to resolve" in error_str or "[Errno -2]" in error_str:
                last_error = (
                    f"DNS resolution failed for {hostname}: {error_str}. "
                    "This may occur when Python's DNS resolver cannot resolve the domain. "
                    "Try configuring DNS servers in Docker or using container names for internal services."
                )
            else:
                last_error = f"Connection error fetching metadata from {metadata_url}: {error_str}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, max_retries)
            
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP error fetching metadata from {metadata_url}: {str(e)}"
            logger.warning("%s (attempt %d/%d)", last_error, attempt, max_retries)
            # Don't retry on HTTP errors (4xx, 5xx) - they're unlikely to resolve
            break
            
        except ValueError as e:
            last_error = f"Invalid metadata response from {metadata_url}: {str(e)}"
            logger.error("%s (attempt %d/%d)", last_error, attempt, max_retries)
            # Don't retry on validation errors
            break
            
        except Exception as e:
            last_error = f"Unexpected error fetching metadata from {metadata_url}: {str(e)}"
            logger.error("%s (attempt %d/%d)", last_error, attempt, max_retries)
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries:
            delay = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
            logger.info("Waiting %d seconds before retry...", delay)
            time.sleep(delay)
    
    # All retries failed
    error_message = (
        f"Failed to fetch OIDC metadata after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
    logger.error(error_message)
    return None, error_message
