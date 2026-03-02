"""
Optional validation gates for invoice PDF and UBL (veraPDF, EN16931).

When configured, export flow can run external validators and surface
actionable failures or summaries in the UI.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET


def validate_ubl_wellformed(ubl_xml: str) -> Tuple[bool, List[str]]:
    """
    Check UBL XML is well-formed and contains Invoice root.
    Returns (passed, list of message strings).
    """
    messages: List[str] = []
    try:
        root = ET.fromstring(ubl_xml)
        local_tag = root.tag.split("}")[-1] if root.tag else ""
        if local_tag != "Invoice":
            messages.append("Root element is not an Invoice.")
            return False, messages
        return True, []
    except ET.ParseError as e:
        messages.append(f"Invalid XML: {e}")
        return False, messages


def validate_pdfa_verapdf(
    pdf_bytes: bytes,
    verapdf_path: Optional[str] = None,
    timeout_s: int = 60,
) -> Tuple[bool, List[str]]:
    """
    Run veraPDF CLI on PDF bytes if path is set.
    Returns (passed, list of validator output lines or error messages).
    """
    path = (verapdf_path or os.getenv("INVOICE_VERAPDF_PATH") or "").strip()
    if not path or not os.path.isfile(path):
        return True, []  # Skip when not configured

    messages: List[str] = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        try:
            tmp.write(pdf_bytes)
            tmp.flush()
            tmp_path = tmp.name
        except Exception as e:
            return False, [f"Could not write temp PDF: {e}"]

    try:
        result = subprocess.run(
            [path, tmp_path, "--format", "text"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode != 0:
            messages.append(f"veraPDF exited with code {result.returncode}")
        for line in (out + "\n" + err).splitlines():
            line = line.strip()
            if line and ("failed" in line.lower() or "error" in line.lower() or "invalid" in line.lower()):
                messages.append(line[:500])
        if messages:
            return False, messages[:20]
        if out:
            messages.append("veraPDF reported issues (see full output).")
            for line in out.splitlines()[:10]:
                if line.strip():
                    messages.append(line.strip()[:300])
        return result.returncode == 0, messages[:20]
    except subprocess.TimeoutExpired:
        return False, ["veraPDF validation timed out."]
    except FileNotFoundError:
        return False, [f"veraPDF not found at {path}"]
    except Exception as e:
        return False, [str(e)]
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
