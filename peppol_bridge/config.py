from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BridgeConfig:
    provider: str
    bridge_auth_token: Optional[str]
    timeout_s: float

    # e-invoice.be
    einvoice_base_url: str
    einvoice_api_key: Optional[str]

    # Peppyrus
    peppyrus_base_url: str
    peppyrus_api_key: Optional[str]

    # getpeppr
    getpeppr_base_url: str
    getpeppr_api_key: Optional[str]

    # Let’s Peppol (hosted)
    letspeppol_base_url: str
    letspeppol_client_id: Optional[str]
    letspeppol_client_secret: Optional[str]
    letspeppol_peppol_id: Optional[str]
    letspeppol_token_url: Optional[str]

    # Generic passthrough
    generic_forward_url: Optional[str]
    generic_forward_token: Optional[str]


def load_config() -> BridgeConfig:
    provider = (os.getenv("PEPPOL_BRIDGE_PROVIDER") or "generic_custom").strip().lower()
    bridge_auth_token = (os.getenv("PEPPOL_BRIDGE_AUTH_TOKEN") or "").strip() or None
    try:
        timeout_s = float((os.getenv("PEPPOL_BRIDGE_TIMEOUT_S") or "30").strip())
    except Exception:
        timeout_s = 30.0

    einvoice_base_url = (os.getenv("EINVOICE_BASE_URL") or "https://api.e-invoice.be").strip().rstrip("/")
    einvoice_api_key = (os.getenv("EINVOICE_API_KEY") or "").strip() or None

    peppyrus_base_url = (os.getenv("PEPPYRUS_BASE_URL") or "https://api.peppyrus.be/v1").strip().rstrip("/")
    peppyrus_api_key = (os.getenv("PEPPYRUS_API_KEY") or "").strip() or None

    getpeppr_base_url = (os.getenv("GETPEPPR_BASE_URL") or "https://api.getpeppr.dev/v1").strip().rstrip("/")
    getpeppr_api_key = (os.getenv("GETPEPPR_API_KEY") or "").strip() or None

    letspeppol_base_url = (os.getenv("LETSPEPPOL_BASE_URL") or "https://be.letspeppol.org").strip().rstrip("/")
    letspeppol_client_id = (os.getenv("LETSPEPPOL_CLIENT_ID") or "").strip() or None
    letspeppol_client_secret = (os.getenv("LETSPEPPOL_CLIENT_SECRET") or "").strip() or None
    letspeppol_peppol_id = (os.getenv("LETSPEPPOL_PEPPOL_ID") or "").strip() or None
    letspeppol_token_url = (os.getenv("LETSPEPPOL_TOKEN_URL") or "").strip() or None

    # Generic passthrough
    generic_forward_url = (os.getenv("GENERIC_FORWARD_URL") or "").strip()
    generic_forward_token = (os.getenv("GENERIC_FORWARD_TOKEN") or "").strip() or None

    return BridgeConfig(
        provider=provider,
        bridge_auth_token=bridge_auth_token,
        timeout_s=timeout_s,
        einvoice_base_url=einvoice_base_url,
        einvoice_api_key=einvoice_api_key,
        peppyrus_base_url=peppyrus_base_url,
        peppyrus_api_key=peppyrus_api_key,
        getpeppr_base_url=getpeppr_base_url,
        getpeppr_api_key=getpeppr_api_key,
        letspeppol_base_url=letspeppol_base_url,
        letspeppol_client_id=letspeppol_client_id,
        letspeppol_client_secret=letspeppol_client_secret,
        letspeppol_peppol_id=letspeppol_peppol_id,
        letspeppol_token_url=letspeppol_token_url,
        generic_forward_url=generic_forward_url or None,
        generic_forward_token=generic_forward_token,
    )
