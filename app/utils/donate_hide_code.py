"""Generate and verify donate-hide codes.

Two modes:

1. **Ed25519 (recommended, no secret on server):**
   You keep a private key; the app only has the public key. You sign the
   system_id; the user enters the base64 signature. The app verifies with
   the public key. Nothing sensitive is stored on the server.

2. **HMAC (legacy):**
   Code = HMAC-SHA256(secret, system_id) as 64 hex chars. Requires the
   secret on the server (env or file).
"""
import base64
import hmac
import hashlib
def compute_donate_hide_code(secret: str, system_id: str) -> str:
    """Compute the donate-hide code (HMAC mode) for a given secret and system ID.

    Args:
        secret: The DONATE_HIDE_UNLOCK_SECRET (must match app config).
        system_id: The instance's system_instance_id (UUID from Settings).

    Returns:
        64-character lowercase hex string (SHA256 digest).
    """
    if not secret or not system_id:
        return ""
    key = secret.encode("utf-8")
    msg = system_id.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_ed25519_signature(signature_b64: str, system_id: str, public_key_pem: str) -> bool:
    """Verify an Ed25519 signature over the system_id (public-key mode).

    Args:
        signature_b64: Base64-encoded signature (what the user enters as the code).
        system_id: The instance's system_instance_id.
        public_key_pem: PEM-encoded Ed25519 public key (bytes or str).

    Returns:
        True if the signature is valid for this system_id and public key.
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature

        sig = base64.standard_b64decode(signature_b64)
        message = system_id.encode("utf-8")
        if isinstance(public_key_pem, bytes):
            public_key_pem = public_key_pem.decode("utf-8")
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        public_key.verify(sig, message)
        return True
    except Exception:
        return False
