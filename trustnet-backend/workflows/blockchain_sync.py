#!/usr/bin/env python3
"""Workflow: Blockchain Sync - Run hourly."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import AsyncSessionLocal
from app.models.postgres import Entity
from app.services.blockchain import BlockchainService
from sqlalchemy import select


async def main():
    service = BlockchainService()
    if not service.enabled:
        print("Blockchain disabled")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Entity).where(Entity.on_chain == False, Entity.aggregate_score < 25).limit(10)
        )
        for entity in result.scalars().all():
            tx = await service.flag_entity(entity.entity_type, entity.entity_value, entity.aggregate_score or 0)
            if tx:
                entity.on_chain = True
                print(f"On-chain: {entity.entity_value} tx={tx}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())