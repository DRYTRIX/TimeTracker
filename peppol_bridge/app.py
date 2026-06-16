from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, jsonify, request

from peppol_bridge.config import BridgeConfig, load_config
from peppol_bridge.providers.base import ProviderBase, ProviderError
from peppol_bridge.providers.einvoice import EInvoiceProvider
from peppol_bridge.providers.generic_custom import GenericCustomProvider
from peppol_bridge.providers.peppyrus import PeppyrusProvider


def _json_error(message: str, status_code: int = 400, *, details: Optional[Dict[str, Any]] = None) -> Response:
    body: Dict[str, Any] = {"ok": False, "error": message}
    if details:
        body["details"] = details
    return jsonify(body), status_code


def _require_bearer(auth_header: str) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2:
        return None
    kind, token = parts[0].strip().lower(), parts[1].strip()
    if kind != "bearer" or not token:
        return None
    return token


def _validate_timetracker_contract(payload: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not isinstance(payload, dict):
        return None, "Payload must be a JSON object"

    recipient = payload.get("recipient")
    sender = payload.get("sender")
    document = payload.get("document")
    pl = payload.get("payload")

    if not isinstance(recipient, dict) or not isinstance(sender, dict) or not isinstance(document, dict) or not isinstance(pl, dict):
        return None, "Missing or invalid recipient/sender/document/payload object"

    ubl_xml = pl.get("ubl_xml")
    if not isinstance(ubl_xml, str) or not ubl_xml.strip():
        return None, "Missing payload.ubl_xml"

    # Minimal routing identifiers (required for Peppyrus; e-invoice derives from UBL but still validate for consistency)
    def _s(obj: Dict[str, Any], k: str) -> str:
        v = obj.get(k)
        return v.strip() if isinstance(v, str) else ""

    out = {
        "recipient_endpoint_id": _s(recipient, "endpoint_id"),
        "recipient_scheme_id": _s(recipient, "scheme_id"),
        "sender_endpoint_id": _s(sender, "endpoint_id"),
        "sender_scheme_id": _s(sender, "scheme_id"),
        "document_id": _s(document, "id"),
        "document_type_id": _s(document, "type_id"),
        "process_id": _s(document, "process_id"),
        "ubl_xml": ubl_xml,
    }
    if not out["sender_endpoint_id"] or not out["sender_scheme_id"]:
        return None, "Missing sender endpoint_id/scheme_id"
    if not out["recipient_endpoint_id"] or not out["recipient_scheme_id"]:
        return None, "Missing recipient endpoint_id/scheme_id"
    if not out["document_id"] or not out["document_type_id"] or not out["process_id"]:
        return None, "Missing document.id/type_id/process_id"

    return out, None


def _build_provider(cfg: BridgeConfig) -> ProviderBase:
    if cfg.provider in {"einvoice", "e-invoice", "e-invoice.be", "einvoice.be"}:
        if not cfg.einvoice_api_key:
            raise ProviderError("EINVOICE_API_KEY is not set")
        return EInvoiceProvider(base_url=cfg.einvoice_base_url, api_key=cfg.einvoice_api_key, timeout_s=cfg.timeout_s)
    if cfg.provider in {"peppyrus"}:
        if not cfg.peppyrus_api_key:
            raise ProviderError("PEPPYRUS_API_KEY is not set")
        return PeppyrusProvider(base_url=cfg.peppyrus_base_url, api_key=cfg.peppyrus_api_key, timeout_s=cfg.timeout_s)
    if cfg.provider in {"generic_custom", "generic"}:
        if not cfg.generic_forward_url:
            raise ProviderError("GENERIC_FORWARD_URL is not set for generic_custom provider")
        return GenericCustomProvider(
            forward_url=cfg.generic_forward_url,
            bearer_token=cfg.generic_forward_token,
            timeout_s=cfg.timeout_s,
        )
    raise ProviderError(f"Unknown PEPPOL_BRIDGE_PROVIDER: {cfg.provider}")


def create_app() -> Flask:
    app = Flask(__name__)
    cfg = load_config()

    @app.get("/health")
    def health() -> Response:
        return jsonify(
            {
                "ok": True,
                "service": "peppol-bridge",
                "provider": cfg.provider,
                "time": int(time.time()),
            }
        )

    @app.post("/test")
    def test() -> Response:
        try:
            provider = _build_provider(cfg)
            data = provider.test_credentials()
            return jsonify({"ok": True, "provider": provider.name, "data": data})
        except ProviderError as e:
            return _json_error(str(e), 400)
        except Exception as e:
            return _json_error(f"Test failed: {e}", 500)

    @app.post("/send")
    def send() -> Response:
        if cfg.bridge_auth_token:
            token = _require_bearer(request.headers.get("Authorization", ""))
            if not token or token != cfg.bridge_auth_token:
                return _json_error("Unauthorized", 401)

        try:
            payload = request.get_json(force=True, silent=False)
        except Exception as e:
            return _json_error(f"Invalid JSON: {e}", 400)

        data, err = _validate_timetracker_contract(payload)
        if err:
            return _json_error(err, 400)

        try:
            provider = _build_provider(cfg)
            result = provider.send_ubl(
                ubl_xml=data["ubl_xml"],
                sender_endpoint_id=data["sender_endpoint_id"],
                sender_scheme_id=data["sender_scheme_id"],
                recipient_endpoint_id=data["recipient_endpoint_id"],
                recipient_scheme_id=data["recipient_scheme_id"],
                document_id=data["document_id"],
                document_type_id=data["document_type_id"],
                process_id=data["process_id"],
            )
            return jsonify({"ok": True, "message_id": result.message_id, "provider": provider.name, "raw": result.raw})
        except ProviderError as e:
            return _json_error(str(e), 502)
        except Exception as e:
            return _json_error(f"Send failed: {e}", 500)

    @app.get("/")
    def index() -> Response:
        return jsonify(
            {
                "service": "peppol-bridge",
                "endpoints": ["/health", "/test", "/send"],
            }
        )

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8088"))
    create_app().run(host="0.0.0.0", port=port)

