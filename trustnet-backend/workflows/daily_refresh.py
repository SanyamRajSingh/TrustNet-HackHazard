#!/usr/bin/env python3
"""
Workflow: Daily Intelligence Refresh
Run via Render cron job or: python workflows/daily_refresh.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import AsyncSessionLocal
from app.models.postgres import Entity
from app.services.neo4j_service import Neo4jService
from app.services.safebrowsing import SafeBrowsingService
from app.services.whois_service import WHOISService
from sqlalchemy import select


async def main():
    whois = WHOISService()
    safebrowse = SafeBrowsingService()
    neo4j = Neo4jService()

    async with AsyncSessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            select(Entity).where(
                (Entity.last_refreshed_at == None) | (Entity.last_refreshed_at < cutoff)
            ).limit(100)
        )
        entities = result.scalars().all()
        print(f"Found {len(entities)} entities to refresh")

        for entity in entities:
            if entity.entity_type != "domain":
                continue
            try:
                whois_data = await whois.lookup_domain(entity.entity_value)
                sb_data = await safebrowse.check_url(entity.entity_value)
                score = whois.calculate_domain_score(whois_data)
                if sb_data.get("flagged"):
                    score = 0
                entity.aggregate_score = score
                entity.last_refreshed_at = datetime.now(timezone.utc)
            except Exception as e:
                print(f"Failed for {entity.entity_value}: {e}")

        await db.commit()
        print(f"Refreshed {len(entities)} entities")


if __name__ == "__main__":
    asyncio.run(main())