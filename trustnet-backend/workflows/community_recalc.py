#!/usr/bin/env python3
"""Workflow: Community Score Recalculation - Run every 30 minutes."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import AsyncSessionLocal
from app.models.postgres import CommunityReport, Entity
from sqlalchemy import func, select


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CommunityReport.entity_id, func.count(CommunityReport.id).label("cnt"))
            .group_by(CommunityReport.entity_id)
        )
        for row in result.all():
            entity = await db.get(Entity, str(row.entity_id))
            if entity:
                entity.aggregate_score = max(0, (entity.aggregate_score or 50) - row.cnt * 5)
        await db.commit()
        print("Community scores recalculated")


if __name__ == "__main__":
    asyncio.run(main())