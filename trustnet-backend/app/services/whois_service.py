"""
WHOIS Service - Domain age and infrastructure intelligence.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class WHOISService:
    """Domain WHOIS lookup using WhoisXML API."""

    def __init__(self):
        self.api_key = settings.WHOIS_API_KEY
        self.base_url = "https://www.whoisxmlapi.com/whoisserver/WhoisService"

    async def lookup_domain(self, domain: str) -> Dict[str, Any]:
        """
        Look up WHOIS data for a domain.
        Returns: dict with age_days, registrar, nameservers, creation_date, etc.
        Falls back to a mock "suspicious new domain" result if the API key is missing.
        """
        if not domain:
            return {"found": False, "reason": "No domain provided"}

        # Clean domain
        domain = domain.lower().strip()
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

        # Fast-path: return mock data if API key is missing/placeholder
        if not self.api_key or self.api_key in ("dummy", ""):
            logger.warning(
                "whois.no_api_key",
                domain=domain,
                msg="WHOIS_API_KEY not set — returning mock domain data (2 days old)",
            )
            return self._mock_domain_data(domain)

        try:
            params = {
                "apiKey": self.api_key,
                "domainName": domain,
                "outputFormat": "JSON",
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.base_url, params=params, timeout=5
                )
                resp.raise_for_status()
                data = resp.json()
                return self._parse_whois_data(domain, data)
        except httpx.HTTPStatusError as e:
            logger.error("whois.http_error", domain=domain, status=e.response.status_code)
        except httpx.TimeoutException:
            logger.warning("whois.timeout", domain=domain)
        except Exception as e:
            logger.error("whois.error", domain=domain, error=str(e))

        # On any error, return mock suspicious data so pipeline continues
        logger.warning("whois.fallback_to_mock", domain=domain)
        return self._mock_domain_data(domain)

    def _mock_domain_data(self, domain: str) -> Dict[str, Any]:
        """
        Return a mock WHOIS result (2 days old = suspicious) for demo/fallback.
        This keeps the scoring pipeline alive when WHOIS_API_KEY is absent.
        """
        return {
            "found": True,
            "domain": domain,
            "age_days": 2,
            "age_years": 0,
            "creation_date": None,
            "registrar": "Unknown (mock fallback)",
            "nameservers": [],
            "has_privacy_protection": False,
            "status": "unknown",
            "_mock": True,
        }


    def _parse_whois_data(self, domain: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse WhoisXML API response into structured format."""
        whois_record = data.get("WhoisRecord", {})
        if not whois_record:
            return {"found": False, "domain": domain}

        # Extract creation date
        created_date_str = whois_record.get("createdDate", "")
        registry_date = whois_record.get("registryData", {}).get("createdDate", "")
        
        age_days = None
        creation_date = None
        for date_str in [created_date_str, registry_date]:
            if date_str:
                try:
                    # Handle various date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%d-%b-%Y"]:
                        try:
                            creation_date = datetime.strptime(date_str[:10], fmt)
                            break
                        except ValueError:
                            continue
                    if creation_date:
                        age_days = (datetime.now() - creation_date).days
                        break
                except Exception:
                    continue

        # Extract registrar
        registrar = (
            whois_record.get("registrarName", "") or
            whois_record.get("registryData", {}).get("registrarName", "Unknown")
        )

        # Extract nameservers
        name_servers = whois_record.get("nameServers", {})
        if isinstance(name_servers, dict):
            host_names = name_servers.get("hostNames", [])
            if isinstance(host_names, str):
                ns_list = [h.strip() for h in host_names.split(",")]
            else:
                ns_list = host_names
        else:
            ns_list = []

        # Privacy protection detection
        has_privacy = any(
            keyword in str(whois_record).lower()
            for keyword in ["privacy", "redacted", "whoisguard", "domains by proxy"]
        )

        return {
            "found": True,
            "domain": domain,
            "age_days": age_days,
            "age_years": age_days / 365 if age_days else None,
            "creation_date": creation_date.isoformat() if creation_date else None,
            "registrar": registrar,
            "nameservers": ns_list,
            "has_privacy_protection": has_privacy,
            "status": whois_record.get("status", "unknown"),
        }

    def calculate_domain_score(self, whois_data: Dict[str, Any]) -> int:
        """
        Calculate domain intelligence score (0-100).
        Lower score = riskier domain.
        """
        if not whois_data.get("found"):
            return 30  # Cannot verify = lower trust

        age_days = whois_data.get("age_days")
        if age_days is None:
            return 35  # Unknown age = moderate risk

        if age_days < 30:
            return 5   # Very new domain - HIGH RISK
        elif age_days < 90:
            return 20  # Recently registered
        elif age_days < 365:
            return 45  # Under 1 year
        elif age_days < 3 * 365:
            return 60  # 1-3 years
        elif age_days < 5 * 365:
            return 75  # 3-5 years
        else:
            return 90  # Well-established domain


class DNSAuthService:
    """DNS-based email authentication checker (SPF, DKIM, DMARC)."""

    async def check_email_auth(self, email_domain: str) -> Dict[str, Any]:
        """
        Check SPF, DKIM, and DMARC records for an email domain.
        Returns: dict with spf, dkim, dmarc, overall_auth_pass.
        """
        import dns.resolver

        result = {
            "domain": email_domain,
            "spf": False,
            "spf_record": None,
            "dkim": False,
            "dkim_record": None,
            "dmarc": False,
            "dmarc_record": None,
            "overall_auth_pass": False,
        }

        # Check SPF
        try:
            answers = dns.resolver.resolve(email_domain, "TXT")
            for rdata in answers:
                txt = str(rdata).replace('"', '')
                if "v=spf1" in txt:
                    result["spf"] = True
                    result["spf_record"] = txt
                    break
        except Exception:
            pass

        # Check DKIM (default selector)
        try:
            answers = dns.resolver.resolve(f"default._domainkey.{email_domain}", "TXT")
            for rdata in answers:
                txt = str(rdata).replace('"', '')
                if "v=DKIM1" in txt:
                    result["dkim"] = True
                    result["dkim_record"] = txt
                    break
        except Exception:
            # Try common selectors
            for selector in ["google", "mail", "selector1", "dkim"]:
                try:
                    answers = dns.resolver.resolve(f"{selector}._domainkey.{email_domain}", "TXT")
                    for rdata in answers:
                        txt = str(rdata).replace('"', '')
                        if "v=DKIM1" in txt or "k=rsa" in txt:
                            result["dkim"] = True
                            result["dkim_record"] = f"selector={selector}"
                            break
                except Exception:
                    continue
                if result["dkim"]:
                    break

        # Check DMARC
        try:
            answers = dns.resolver.resolve(f"_dmarc.{email_domain}", "TXT")
            for rdata in answers:
                txt = str(rdata).replace('"', '')
                if "v=DMARC1" in txt:
                    result["dmarc"] = True
                    result["dmarc_record"] = txt
                    break
        except Exception:
            pass

        # Overall: pass if at least SPF + DMARC
        result["overall_auth_pass"] = result["spf"] and result["dmarc"]
        result["score"] = self._calculate_auth_score(result)

        return result

    def _calculate_auth_score(self, auth_result: Dict[str, Any]) -> int:
        """Calculate communication channel integrity score from DNS auth results."""
        score = 20  # Base score
        if auth_result.get("spf"):
            score += 20
        if auth_result.get("dkim"):
            score += 20
        if auth_result.get("dmarc"):
            score += 25
        if auth_result.get("overall_auth_pass"):
            score += 15
        return min(100, score)

    def is_disposable_email(self, email: str) -> bool:
        """Check if email is from a disposable provider."""
        disposable_domains = {
            "tempmail.com", "guerrillamail.com", "10minutemail.com",
            "mailinator.com", "throwaway.email", "yopmail.com",
            "getairmail.com", "burnermail.io", "temp-mail.org",
            "fake-email.net", "sharklasers.com", "trbvm.com",
            "mailnesia.com", "mailcatch.com", "dispostable.com",
        }
        domain = email.split("@")[-1].lower() if "@" in email else ""
        return domain in disposable_domains or "temp" in domain
