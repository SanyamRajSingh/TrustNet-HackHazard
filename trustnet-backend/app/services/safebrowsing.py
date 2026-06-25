"""
Google Safe Browsing API Service
URL reputation checking for malware and phishing.
"""

from typing import Any, Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class SafeBrowsingService:
    """Google Safe Browsing API v4 integration."""

    def __init__(self):
        self.api_key = settings.GOOGLE_SAFE_BROWSING_KEY
        self.base_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

    async def check_url(self, url: str) -> Dict[str, Any]:
        """
        Check if URL is flagged by Google Safe Browsing.
        Returns: dict with flagged(bool), threat_types.
        """
        if not url:
            return {"checked": False, "flagged": False}

        try:
            payload = {
                "client": {
                    "clientId": "trustnet",
                    "clientVersion": "1.0.0",
                },
                "threatInfo": {
                    "threatTypes": [
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE",
                        "POTENTIALLY_HARMFUL_APPLICATION",
                    ],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": url}],
                },
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}?key={self.api_key}",
                    json=payload,
                    timeout=5,
                )
                resp.raise_for_status()
                data = resp.json()
                matches = data.get("matches", [])
                if matches:
                    threats = [m.get("threatType") for m in matches]
                    logger.warning("safebrowsing.flagged", url=url, threats=threats)
                    return {
                        "checked": True,
                        "flagged": True,
                        "threat_types": threats,
                        "score": 0,  # Flagged = 0 score
                    }
                return {"checked": True, "flagged": False, "score": 100}
        except httpx.HTTPStatusError as e:
            logger.error("safebrowsing.http_error", status=e.response.status_code)
        except httpx.TimeoutException:
            logger.warning("safebrowsing.timeout", url=url)
        except Exception as e:
            logger.error("safebrowsing.error", error=str(e))

        return {"checked": False, "flagged": False, "score": 50}


class PhishTankService:
    """PhishTank community phishing database lookup."""

    def __init__(self):
        self.api_key = settings.PHISHTANK_API_KEY
        self.base_url = "https://checkurl.phishtank.com/checkurl/"

    async def check_url(self, url: str) -> Dict[str, Any]:
        """Check if URL is in PhishTank database."""
        if not url:
            return {"checked": False, "flagged": False}

        try:
            import urllib.parse
            encoded = urllib.parse.quote(url, safe="")
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.base_url,
                    data={"url": encoded, "format": "json", "app_key": self.api_key},
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", {})
                    if results.get("valid") and results.get("in_database"):
                        if results.get("verified"):
                            logger.warning("phishtank.flagged", url=url)
                            return {
                                "checked": True,
                                "flagged": True,
                                "verified": True,
                                "score": 0,
                            }
                    return {"checked": True, "flagged": False, "score": 100}
        except Exception as e:
            logger.warning("phishtank.error", error=str(e))

        return {"checked": False, "flagged": False, "score": 50}


class URLhausService:
    """abuse.ch URLhaus malware URL database lookup."""

    async def check_url(self, url: str) -> Dict[str, Any]:
        """Check if URL is in URLhaus malware database."""
        if not url:
            return {"checked": False, "flagged": False}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://urlhaus-api.abuse.ch/v1/url/",
                    data={"url": url},
                    timeout=5,
                    headers={"Auth-Key": ""},  # No auth required for basic lookups
                )
                if resp.status_code == 200:
                    data = resp.json()
                    query_status = data.get("query_status")
                    if query_status == "no_results":
                        return {"checked": True, "flagged": False, "score": 100}
                    elif query_status == "ok" and data.get("url_status") != "online":
                        return {
                            "checked": True,
                            "flagged": True,
                            "threat": data.get("threat", "malware"),
                            "score": 0,
                        }
        except Exception as e:
            logger.warning("urlhaus.error", error=str(e))

        return {"checked": False, "flagged": False, "score": 50}