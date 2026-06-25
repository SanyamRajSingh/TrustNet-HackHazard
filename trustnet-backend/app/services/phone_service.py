"""
Phone Verification Service
NumVerify integration for carrier and line type validation.
"""

from typing import Any, Dict, Optional

import httpx
import phonenumbers
import structlog

from config import settings

logger = structlog.get_logger()


class PhoneService:
    """Phone number validation using phonenumbers library + NumVerify API."""

    def __init__(self):
        self.api_key = settings.NUMVERIFY_API_KEY
        self.base_url = "http://apilayer.net/api/validate"

    async def verify_phone(self, phone: str) -> Dict[str, Any]:
        """
        Verify phone number - validate format, carrier, line type.
        Falls back to local phonenumbers-only validation if NUMVERIFY_API_KEY is missing.
        Returns: dict with valid(bool), carrier, line_type, location.
        """
        result = {
            "phone": phone,
            "valid": False,
            "carrier": None,
            "line_type": None,
            "location": None,
            "country_code": None,
            "score": 0,
        }

        if not phone:
            return result

        # Parse with phonenumbers library (always runs — free, no API key needed)
        try:
            parsed = phonenumbers.parse(phone, "IN")  # Default to India
            if phonenumbers.is_valid_number(parsed):
                result["valid"] = True
                result["country_code"] = f"+{parsed.country_code}"
                result["line_type"] = self._get_line_type(parsed)
                result["location"] = phonenumbers.geocoder.description_for_number(parsed, "en")
        except phonenumbers.NumberParseException:
            result["score"] = self._calculate_phone_score(result)
            return result

        # NumVerify for carrier info — skip if key missing/dummy
        if not self.api_key or self.api_key in ("dummy", ""):
            logger.warning(
                "numverify.no_api_key",
                phone=phone,
                msg="NUMVERIFY_API_KEY not set — using phonenumbers-only result",
            )
            result["carrier"] = "Unknown (mock fallback)"
            result["score"] = self._calculate_phone_score(result)
            return result

        try:
            params = {
                "access_key": self.api_key,
                "number": phone.replace("+", ""),
                "country_code": "IN",
                "format": 1,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.base_url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("valid"):
                        result["carrier"] = data.get("carrier")
                        result["line_type"] = data.get("line_type")
                        result["location"] = data.get("location")
        except Exception as e:
            logger.warning("numverify.error — using phonenumbers-only result", error=str(e))

        result["score"] = self._calculate_phone_score(result)
        return result


    def _get_line_type(self, parsed) -> str:
        """Determine line type from parsed number."""
        num_type = phonenumbers.number_type(parsed)
        type_map = {
            phonenumbers.PhoneNumberType.MOBILE: "mobile",
            phonenumbers.PhoneNumberType.FIXED_LINE: "landline",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
            phonenumbers.PhoneNumberType.VOIP: "voip",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
            phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
        }
        return type_map.get(num_type, "unknown")

    def _calculate_phone_score(self, result: Dict[str, Any]) -> int:
        """Calculate phone risk score (0-100, higher = more trustworthy)."""
        if not result.get("valid"):
            return 15  # Invalid number = suspicious

        score = 60  # Base for valid number

        # Line type adjustments
        line_type = result.get("line_type", "").lower()
        if line_type == "mobile":
            score += 15
        elif line_type == "landline":
            score += 10
        elif line_type in ["voip", "premium_rate"]:
            score -= 30  # VoIP often used by scammers
        elif line_type == "toll_free":
            score += 0

        return min(100, max(0, score))
