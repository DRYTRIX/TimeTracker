"""
OCR utilities for receipt scanning and text extraction.

This module provides functionality to extract text and data from receipt images
using Tesseract OCR and parse common receipt information.
"""

import os
import re
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Check if Tesseract is available
try:
    import pytesseract
    from PIL import Image

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract or PIL not installed. Receipt OCR will not be available.")


def is_ocr_available():
    """Check if OCR functionality is available"""
    return TESSERACT_AVAILABLE


def extract_text_from_image(image_path, lang="eng"):
    """
    Extract text from an image using Tesseract OCR.

    Args:
        image_path: Path to the image file
        lang: OCR language (default: 'eng', can be 'eng+deu' for multilingual)

    Returns:
        Extracted text as string
    """
    if not TESSERACT_AVAILABLE:
        raise RuntimeError("Tesseract OCR is not available. Install pytesseract and PIL.")

    try:
        # Open and preprocess image
        image = Image.open(image_path)

        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Extract text
        text = pytesseract.image_to_string(image, lang=lang)

        return text
    except Exception as e:
        logger.error(f"Error extracting text from image {image_path}: {e}")
        raise


def parse_receipt_data(text):
    """
    Parse common receipt information from extracted text.

    Args:
        text: Extracted text from receipt

    Returns:
        Dictionary with parsed data (vendor, date, total, items, etc.)
    """
    data = {
        "vendor": None,
        "date": None,
        "total": None,
        "tax": None,
        "subtotal": None,
        "items": [],
        "currency": "EUR",
        "raw_text": text,
    }

    lines = text.split("\n")

    # Try to extract vendor (usually first few lines)
    vendor_lines = []
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) > 3:
            vendor_lines.append(line)

    if vendor_lines:
        data["vendor"] = vendor_lines[0]

    # Extract amounts
    amounts = extract_amounts(text)
    if amounts:
        # Try to identify total (usually largest amount or labeled as total)
        total_candidates = []

        for amount_info in amounts:
            label = amount_info.get("label", "").lower()
            if any(keyword in label for keyword in ["total", "gesamt", "suma", "totale"]):
                data["total"] = amount_info["amount"]
            elif any(keyword in label for keyword in ["tax", "vat", "mwst", "iva", "tva"]):
                data["tax"] = amount_info["amount"]
            elif any(keyword in label for keyword in ["subtotal", "zwischensumme", "sous-total"]):
                data["subtotal"] = amount_info["amount"]
            else:
                total_candidates.append(amount_info["amount"])

        # If no labeled total found, use the largest amount
        if not data["total"] and total_candidates:
            data["total"] = max(total_candidates)

    # Extract date
    date = extract_date(text)
    if date:
        data["date"] = date

    # Extract currency
    currency = extract_currency(text)
    if currency:
        data["currency"] = currency

    return data


def extract_amounts(text):
    """
    Extract monetary amounts from text.

    Returns:
        List of dictionaries with 'amount' and 'label' keys
    """
    amounts = []

    # Patterns for amounts (supports various formats)
    # Examples: 12.34, 12,34, $12.34, €12,34, 12.34 EUR
    patterns = [
        r"([A-Za-z\s]*?)\s*([$€£¥]?)\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*([A-Z]{3})?",
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            label = match.group(1).strip() if match.group(1) else ""
            symbol = match.group(2) if match.group(2) else ""
            amount_str = match.group(3)
            currency = match.group(4) if match.group(4) else ""

            # Normalize amount (convert comma to dot if needed)
            # Determine if comma or dot is decimal separator
            if "," in amount_str and "." in amount_str:
                # Has both, assume European format (1.234,56)
                amount_str = amount_str.replace(".", "").replace(",", ".")
            elif "," in amount_str:
                # Only comma, check if it's thousands separator or decimal
                parts = amount_str.split(",")
                if len(parts) == 2 and len(parts[1]) == 2:
                    # Likely decimal separator
                    amount_str = amount_str.replace(",", ".")
                else:
                    # Likely thousands separator
                    amount_str = amount_str.replace(",", "")

            try:
                amount = Decimal(amount_str)
                amounts.append({"amount": amount, "label": label, "symbol": symbol, "currency": currency})
            except (ValueError, Decimal.InvalidOperation):
                continue

    return amounts


def extract_date(text):
    """
    Extract date from receipt text.

    Returns:
        datetime.date object or None
    """
    # Common date patterns
    patterns = [
        r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})",  # DD/MM/YYYY or MM/DD/YYYY
        r"(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})",  # YYYY-MM-DD
        r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{2,4})",  # DD Month YYYY
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()

                if len(groups) == 3:
                    if pattern == patterns[0]:  # DD/MM/YYYY or MM/DD/YYYY
                        # Try DD/MM/YYYY first (European format)
                        try:
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                            if year < 100:
                                year += 2000
                            return datetime(year, month, day).date()
                        except ValueError:
                            # Try MM/DD/YYYY (US format)
                            try:
                                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                                if year < 100:
                                    year += 2000
                                return datetime(year, month, day).date()
                            except ValueError:
                                continue

                    elif pattern == patterns[1]:  # YYYY-MM-DD
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        return datetime(year, month, day).date()

                    elif pattern == patterns[2]:  # DD Month YYYY
                        day = int(groups[0])
                        month_str = groups[1].lower()
                        year = int(groups[2])
                        if year < 100:
                            year += 2000

                        months = {
                            "jan": 1,
                            "feb": 2,
                            "mar": 3,
                            "apr": 4,
                            "may": 5,
                            "jun": 6,
                            "jul": 7,
                            "aug": 8,
                            "sep": 9,
                            "oct": 10,
                            "nov": 11,
                            "dec": 12,
                        }
                        month = months.get(month_str[:3])
                        if month:
                            return datetime(year, month, day).date()

            except (ValueError, TypeError):
                continue

    return None


def extract_currency(text):
    """
    Extract currency code from receipt text.

    Returns:
        3-letter currency code (ISO 4217) or 'EUR' as default
    """
    # Currency symbols and their codes
    currency_symbols = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "Fr": "CHF"}

    # Look for currency symbols
    for symbol, code in currency_symbols.items():
        if symbol in text:
            return code

    # Look for currency codes (3 uppercase letters)
    currency_pattern = r"\b([A-Z]{3})\b"
    matches = re.findall(currency_pattern, text)

    # Common currency codes
    common_currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "INR"]

    for match in matches:
        if match in common_currencies:
            return match

    return "EUR"  # Default


def scan_receipt(image_path, lang="eng"):
    """
    Scan a receipt image and extract structured data.

    Args:
        image_path: Path to the receipt image
        lang: OCR language(s) to use (e.g., 'eng', 'eng+deu')

    Returns:
        Dictionary with extracted receipt data
    """
    if not is_ocr_available():
        return {
            "error": "OCR not available",
            "message": "Please install pytesseract and Pillow: pip install pytesseract pillow",
        }

    try:
        # Extract text
        text = extract_text_from_image(image_path, lang=lang)

        # Parse data
        data = parse_receipt_data(text)

        return data

    except Exception as e:
        logger.error(f"Error scanning receipt {image_path}: {e}")
        return {"error": str(e), "message": "Failed to scan receipt"}


def get_suggested_expense_data(receipt_data):
    """
    Convert receipt data to expense form data suggestions.

    Args:
        receipt_data: Dictionary returned by scan_receipt()

    Returns:
        Dictionary with suggested expense data
    """
    suggestions = {}

    if receipt_data.get("vendor"):
        suggestions["vendor"] = receipt_data["vendor"]
        suggestions["title"] = f"Receipt from {receipt_data['vendor']}"

    if receipt_data.get("total"):
        suggestions["amount"] = float(receipt_data["total"])

    if receipt_data.get("tax"):
        suggestions["tax_amount"] = float(receipt_data["tax"])

    if receipt_data.get("date"):
        suggestions["expense_date"] = receipt_data["date"].isoformat()

    if receipt_data.get("currency"):
        suggestions["currency_code"] = receipt_data["currency"]

    return suggestions
