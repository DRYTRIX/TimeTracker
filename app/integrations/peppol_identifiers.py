"""
PEPPOL participant identifier validation (scheme + endpoint ID).

Validates and normalizes sender/recipient identifiers before submission
to avoid malformed IDs and improve validator compliance.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

# Common PEPPOL participant identifier schemes (ISO 6523)
# See PEPPOL IC and country-specific scheme lists
KNOWN_SCHEMES = frozenset({
    "0007", "0088", "0060", "0130", "0184", "0190", "0191", "0192", "0193",
    "0195", "0196", "0198", "0199", "0200", "0201", "0202", "0204", "0208",
    "0209", "0210", "0211", "0212", "0213", "0215", "0216", "0218", "0219",
    "0220", "0221", "0222", "0223", "0224", "0225", "0226", "0227", "0228",
    "0229", "0230", "0231", "0232", "0233", "0234", "0235", "0236", "0237",
    "0238", "0239", "0240", "0241", "0242", "0243", "0244", "0245", "0246",
    "0247", "0248", "0249", "0250", "0251", "0252", "0253", "0254", "0255",
    "0256", "0257", "0258", "0259", "0260", "0261", "0262", "0263", "0264",
    "0265", "0266", "0267", "0268", "0269", "0270", "0271", "0272", "0273",
    "0274", "0275", "0276", "0277", "0278", "0279", "0280", "0281", "0282",
    "0283", "0284", "0285", "0286", "0287", "0288", "0289", "0290", "0291",
    "0292", "0293", "0294", "0295", "0296", "0297", "0298", "0299", "0300",
    "9915", "9925", "9933", "9944", "9950", "9952", "9954", "9955", "9956",
    "9957", "9958", "9959", "9960", "9961", "9962", "9963", "9964", "9965",
    "9966", "9967", "9968", "9969", "9970", "9971", "9972", "9973", "9974",
    "9975", "9976", "9977", "9978", "9979", "9980", "9981", "9982", "9983",
    "9984", "9985", "9986", "9987", "9988", "9989", "9990", "9991", "9992",
    "9993", "9994", "9995", "9996", "9997", "9998", "9999",
})

# Endpoint ID: alphanumeric, some schemes allow colon/dash (e.g. 0088:1234567890123)
_ENDPOINT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-.:]+$")


class PeppolIdentifierError(ValueError):
    """Raised when a PEPPOL participant identifier is invalid."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


def validate_scheme_id(scheme_id: Optional[str], field: str = "scheme_id") -> str:
    """
    Validate and return normalized scheme ID.
    Raises PeppolIdentifierError if invalid.
    """
    if not scheme_id or not str(scheme_id).strip():
        raise PeppolIdentifierError("Participant scheme ID is required", field=field)
    s = str(scheme_id).strip()
    if not s.isdigit() and s not in KNOWN_SCHEMES:
        # Allow unknown numeric schemes (4 digits typical)
        if not (len(s) <= 10 and all(c.isdigit() for c in s)):
            raise PeppolIdentifierError(
                f"Invalid participant scheme ID: must be numeric or known scheme (e.g. 0088, 9915)",
                field=field,
            )
    return s


def validate_endpoint_id(endpoint_id: Optional[str], field: str = "endpoint_id") -> str:
    """
    Validate and return normalized endpoint ID.
    Raises PeppolIdentifierError if invalid.
    """
    if not endpoint_id or not str(endpoint_id).strip():
        raise PeppolIdentifierError("Participant endpoint ID is required", field=field)
    e = str(endpoint_id).strip()
    if len(e) > 200:
        raise PeppolIdentifierError("Endpoint ID must be at most 200 characters", field=field)
    if not _ENDPOINT_ID_PATTERN.match(e):
        raise PeppolIdentifierError(
            "Endpoint ID may only contain letters, digits, and _ - . :",
            field=field,
        )
    return e


def validate_participant_identifiers(
    sender_endpoint_id: str,
    sender_scheme_id: str,
    recipient_endpoint_id: str,
    recipient_scheme_id: str,
) -> Tuple[Tuple[str, str], Tuple[str, str]]:
    """
    Validate sender and recipient identifiers.
    Returns ((sender_endpoint_id, sender_scheme_id), (recipient_endpoint_id, recipient_scheme_id)).
    Raises PeppolIdentifierError if any identifier is invalid.
    """
    s_ep = validate_endpoint_id(sender_endpoint_id, "sender_endpoint_id")
    s_sch = validate_scheme_id(sender_scheme_id, "sender_scheme_id")
    r_ep = validate_endpoint_id(recipient_endpoint_id, "recipient_endpoint_id")
    r_sch = validate_scheme_id(recipient_scheme_id, "recipient_scheme_id")
    return (s_ep, s_sch), (r_ep, r_sch)
