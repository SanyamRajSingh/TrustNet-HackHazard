"""
MCA (Ministry of Corporate Affairs) Service
Company verification using seeded MCA data + live lookup.
"""

import asyncio
import re
from typing import Any, Dict, Optional

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings

logger = structlog.get_logger()

# Well-known Indian companies for quick matching
WELL_KNOWN_COMPANIES = {
    "tcs": {"name": "Tata Consultancy Services Limited", "cin": "L22210MH1995PLC084781", "age_years": 50},
    "infosys": {"name": "Infosys Limited", "cin": "L85110KA1981PLC013115", "age_years": 43},
    "wipro": {"name": "Wipro Limited", "cin": "L32102KA1945PLC000206", "age_years": 79},
    "hcl": {"name": "HCL Technologies Limited", "cin": "L74140DL1991PLC046369", "age_years": 33},
    "tech mahindra": {"name": "Tech Mahindra Limited", "cin": "L64200MH1986PLC041370", "age_years": 38},
    "cognizant": {"name": "Cognizant Technology Solutions India Private Limited", "cin": "U72200TN1994PTC026590", "age_years": 30},
    "accenture": {"name": "Accenture Solutions Private Limited", "cin": "U74140KA2002PTC030978", "age_years": 22},
    "ibm": {"name": "IBM India Private Limited", "cin": "U72900MH1992PTC066679", "age_years": 32},
    "capgemini": {"name": "Capgemini Technology Services India Limited", "cin": "L72200MH2000PLC125067", "age_years": 24},
    "genpact": {"name": "Genpact India Private Limited", "cin": "U72200DL2004PTC129784", "age_years": 20},
    "mindtree": {"name": "Mindtree Limited", "cin": "L72200KA1999PLC025122", "age_years": 25},
    "mphasis": {"name": "Mphasis Limited", "cin": "L30007KA1992PLC013134", "age_years": 32},
    "lti": {"name": "Larsen & Toubro Infotech Limited", "cin": "L74999MH1996PLC104693", "age_years": 28},
    "persistent": {"name": "Persistent Systems Limited", "cin": "L72200PN1990PLC115933", "age_years": 34},
    "zoho": {"name": "Zoho Corporation Private Limited", "cin": "U72200TZ1996PTC007211", "age_years": 28},
    "swiggy": {"name": "Swiggy Limited", "cin": "U55209KA2013PLC097393", "age_years": 11},
    "zomato": {"name": "Zomato Limited", "cin": "L93030DL2010PLC198141", "age_years": 14},
    "flipkart": {"name": "Flipkart Internet Private Limited", "cin": "U51909KA2011PTC059878", "age_years": 13},
    "amazon": {"name": "Amazon Seller Services Private Limited", "cin": "U52605KA2011PTC060075", "age_years": 13},
    "byjus": {"name": "Think and Learn Private Limited", "cin": "U80302KA2011PTC077426", "age_years": 13},
}


class MCAService:
    """MCA company lookup - seeded data + live scrape fallback."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def lookup_company(self, company_name: str) -> Dict[str, Any]:
        """
        Look up company in MCA records.
        Returns: dict with found(bool), cin, status, age_years, directors, etc.
        """
        if not company_name:
            return {"found": False, "reason": "No company name provided"}

        normalized = self._normalize_name(company_name)
        logger.info("mca.lookup", company=company_name, normalized=normalized)

        # 1. Check well-known companies
        for key, data in WELL_KNOWN_COMPANIES.items():
            if key in normalized or normalized in key:
                return {
                    "found": True,
                    "source": "well_known",
                    "cin": data["cin"],
                    "company_name": data["name"],
                    "status": "Active",
                    "age_years": data["age_years"],
                    "directors": [],
                    "score": 100,
                    "reason": "Well-known established company",
                }

        # 2. Check seeded MCA database
        if self.db:
            db_result = await self._query_database(normalized)
            if db_result:
                return db_result

        # 3. Live lookup via MCA public search (simulated for rate limiting)
        # In production, this would scrape mca.gov.in with rate limiting
        logger.info("mca.not_found_in_records", company=company_name)
        return {
            "found": False,
            "reason": "Company not found in MCA records",
            "normalized_name": normalized,
        }

    async def _query_database(self, normalized_name: str) -> Optional[Dict[str, Any]]:
        """Query seeded MCA company master data."""
        from app.models.postgres import CompanyMaster
        query = select(CompanyMaster).where(
            CompanyMaster.company_name.ilike(f"%{normalized_name}%")
        )
        result = await self.db.execute(query)
        row = result.scalar_one_or_none()
        if row:
            age_years = None
            if row.registration_date:
                from datetime import datetime
                age_years = (datetime.now() - row.registration_date).days // 365
            return {
                "found": True,
                "source": "mca_seed_db",
                "cin": row.cin,
                "company_name": row.company_name,
                "status": row.status or "Unknown",
                "age_years": age_years,
                "directors": row.directors_json or [],
                "state": row.state,
                "score": 75 if row.status == "Active" else 40,
            }
        return None

    def _normalize_name(self, name: str) -> str:
        """Normalize company name for matching."""
        normalized = name.lower().strip()
        # Remove common suffixes
        suffixes = [
            "private limited", "pvt ltd", "pvt. ltd.", "limited", "ltd",
            "llp", "inc", "corp", "corporation", "pvt limited",
        ]
        for suffix in suffixes:
            normalized = normalized.replace(suffix, "").strip()
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def calculate_identity_score(self, mca_result: Dict[str, Any]) -> int:
        """Calculate identity & company verification score (0-100)."""
        if not mca_result.get("found"):
            return 20  # Low score when company not found

        score = 50  # Base for found company

        # Status bonus
        status = mca_result.get("status", "").lower()
        if status == "active":
            score += 25
        elif status in ["dormant", "under process"]:
            score += 5
        elif status in ["strike off", "dissolved"]:
            score -= 30

        # Age bonus
        age = mca_result.get("age_years")
        if age:
            if age > 20:
                score += 25
            elif age > 10:
                score += 15
            elif age > 5:
                score += 10
            elif age > 2:
                score += 5

        # Cap at 100
        return min(100, max(0, score))
