"""
Enhanced OCR Service with better receipt scanning
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
import logging
import re
from app.utils.ocr import scan_receipt, extract_text_from_image, is_ocr_available

logger = logging.getLogger(__name__)


class EnhancedOCRService:
    """Enhanced OCR service with improved receipt parsing"""

    def scan_receipt_enhanced(self, image_path: str, lang: str = "eng") -> Dict[str, Any]:
        """Enhanced receipt scanning with better data extraction"""
        if not is_ocr_available():
            return {"error": "OCR not available"}

        try:
            # Extract text
            text = extract_text_from_image(image_path, lang=lang)
            
            if not text:
                return {"error": "No text extracted from image"}

            # Enhanced parsing
            data = {
                "raw_text": text,
                "merchant": self._extract_merchant(text),
                "date": self._extract_date(text),
                "total": self._extract_total(text),
                "tax": self._extract_tax(text),
                "items": self._extract_items(text),
                "currency": self._extract_currency(text),
                "receipt_number": self._extract_receipt_number(text),
                "confidence": self._calculate_confidence(text)
            }

            return data

        except Exception as e:
            logger.error(f"Error in enhanced receipt scanning: {e}")
            return {"error": str(e)}

    def _extract_merchant(self, text: str) -> Optional[str]:
        """Extract merchant name (usually first line)"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return None

        # First non-empty line is often merchant name
        merchant = lines[0]
        
        # Clean up common OCR artifacts
        merchant = re.sub(r'[^\w\s&.-]', '', merchant)
        merchant = merchant.strip()

        return merchant if len(merchant) > 2 else None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from receipt"""
        # Common date patterns
        patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'\d{1,2}\s+\w{3,9}\s+\d{2,4}',
            r'\w{3,9}\s+\d{1,2},?\s+\d{4}',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(0)
                    # Try to parse and normalize
                    return date_str
                except Exception:
                    continue

        return None

    def _extract_total(self, text: str) -> Optional[Decimal]:
        """Extract total amount"""
        # Look for "TOTAL", "TOTAL DUE", "AMOUNT", etc.
        patterns = [
            r'TOTAL[:\s]+[\$€£¥]?([\d,]+\.?\d*)',
            r'AMOUNT[:\s]+[\$€£¥]?([\d,]+\.?\d*)',
            r'DUE[:\s]+[\$€£¥]?([\d,]+\.?\d*)',
            r'[\$€£¥]([\d,]+\.?\d{2})\s*$',  # Amount at end of line
        ]

        amounts = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    amount_str = match.group(1).replace(',', '')
                    amount = Decimal(amount_str)
                    amounts.append(amount)
                except Exception:
                    continue

        # Return largest amount (likely the total)
        if amounts:
            return max(amounts)

        return None

    def _extract_tax(self, text: str) -> Optional[Decimal]:
        """Extract tax amount"""
        patterns = [
            r'TAX[:\s]+[\$€£¥]?([\d,]+\.?\d*)',
            r'VAT[:\s]+[\$€£¥]?([\d,]+\.?\d*)',
            r'SALES\s+TAX[:\s]+[\$€£¥]?([\d,]+\.?\d*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    tax_str = match.group(1).replace(',', '')
                    return Decimal(tax_str)
                except Exception:
                    continue

        return None

    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from receipt"""
        items = []
        lines = text.split('\n')

        # Pattern: description followed by amount
        item_pattern = re.compile(r'^(.+?)\s+[\$€£¥]?([\d,]+\.?\d{2})$')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = item_pattern.match(line)
            if match:
                description = match.group(1).strip()
                amount_str = match.group(2).replace(',', '')
                
                # Skip totals and tax lines
                if any(keyword in description.upper() for keyword in ['TOTAL', 'TAX', 'SUB', 'AMOUNT', 'DUE']):
                    continue

                try:
                    amount = Decimal(amount_str)
                    items.append({
                        "description": description,
                        "amount": float(amount)
                    })
                except Exception:
                    continue

        return items

    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract currency symbol"""
        currency_symbols = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
            '₹': 'INR',
        }

        for symbol, code in currency_symbols.items():
            if symbol in text:
                return code

        # Check for currency codes
        currency_code_pattern = r'\b(USD|EUR|GBP|JPY|INR|CAD|AUD)\b'
        match = re.search(currency_code_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        return None

    def _extract_receipt_number(self, text: str) -> Optional[str]:
        """Extract receipt/invoice number"""
        patterns = [
            r'RECEIPT[#:\s]+(\w+)',
            r'INVOICE[#:\s]+(\w+)',
            r'#\s*(\d{4,})',
            r'NO[.:\s]+(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for extracted data"""
        confidence = 0.0

        # Check for key indicators
        if len(text) > 50:
            confidence += 0.2
        if re.search(r'[\$€£¥]', text):
            confidence += 0.2
        if re.search(r'TOTAL|AMOUNT|DUE', text, re.IGNORECASE):
            confidence += 0.2
        if re.search(r'\d{1,2}[/-]\d{1,2}', text):
            confidence += 0.2
        if re.search(r'\d+\.\d{2}', text):
            confidence += 0.2

        return min(confidence, 1.0)

