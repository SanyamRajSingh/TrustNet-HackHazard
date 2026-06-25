"""
Celery Tasks
Background intelligence refresh, community recalc, blockchain sync.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import structlog

from app.workers.celery_app import celery_app
from config import settings

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def daily_refresh(self):
    """
    Daily OSINT refresh workflow:
    1. Query entities where last_refreshed < 7 days ago
    2. Re-run WHOIS, Safe Browsing, PhishTank checks
    3. Update risk_score in Neo4j
    4. Recalculate aggregate trust scores in PostgreSQL
    """
    logger.info("workflow.daily_refresh.started")
    try:
        # Run async code in sync context
        asyncio.run(_async_daily_refresh())
        logger.info("workflow.daily_refresh.completed")
        return {"status": "completed", "refreshed": 0}
    except Exception as exc:
        logger.error("workflow.daily_refresh.error", error=str(exc))
        raise self.retry(exc=exc)


async def _async_daily_refresh():
    """Async implementation of daily refresh."""
    from app.models.database import AsyncSessionLocal
    from app.models.postgres import Entity
    from app.services.neo4j_service import Neo4jService
    from app.services.safebrowsing import SafeBrowsingService
    from app.services.whois_service import WHOISService
    from sqlalchemy import select

    whois_service = WHOISService()
    safebrowsing_service = SafeBrowsingService()
    neo4j_service = Neo4jService()

    async with AsyncSessionLocal() as db:
        # Find entities not refreshed in 7 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            select(Entity).where(
                (Entity.last_refreshed_at == None) | (Entity.last_refreshed_at < cutoff)
            ).limit(100)
        )
        entities = result.scalars().all()

        for entity in entities:
            if entity.entity_type == "domain":
                try:
                    whois_data = await whois_service.lookup_domain(entity.entity_value)
                    sb_data = await safebrowsing_service.check_url(entity.entity_value)

                    # Update entity score
                    new_score = whois_service.calculate_domain_score(whois_data)
                    if sb_data.get("flagged"):
                        new_score = 0
                    entity.aggregate_score = new_score
                    entity.last_refreshed_at = datetime.now(timezone.utc)

                    # Update Neo4j
                    await neo4j_service.upsert_entities_from_investigation(
                        {"website_url": entity.entity_value},
                        new_score,
                        "refresh",
                    )
                except Exception as e:
                    logger.warning("refresh.entity_failed", entity=entity.entity_value, error=str(e))

        await db.commit()
        logger.info("workflow.daily_refresh.refreshed", count=len(entities))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def community_recalc(self):
    """
    Community score recalculation workflow:
    1. Pull new community_reports since last run
    2. Recalculate weighted community score per entity
    3. If entity crosses HIGH_RISK threshold: queue blockchain write
    """
    logger.info("workflow.community_recalc.started")
    try:
        asyncio.run(_async_community_recalc())
        logger.info("workflow.community_recalc.completed")
        return {"status": "completed"}
    except Exception as exc:
        logger.error("workflow.community_recalc.error", error=str(exc))
        raise self.retry(exc=exc)


async def _async_community_recalc():
    """Async implementation of community recalc."""
    from app.models.database import AsyncSessionLocal
    from app.models.postgres import CommunityReport, Entity
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as db:
        # Get entities with new reports
        result = await db.execute(
            select(
                CommunityReport.entity_id,
                func.count(CommunityReport.id).label("report_count"),
                func.sum(CommunityReport.loss_amount_inr).label("total_loss"),
            )
            .where(CommunityReport.verified_by_admin == True)
            .group_by(CommunityReport.entity_id)
        )
        rows = result.all()

        for row in rows:
            entity_result = await db.execute(
                select(Entity).where(Entity.id == str(row.entity_id))
            )
            entity = entity_result.scalar_one_or_none()
            if entity:
                # Adjust score based on verified scam reports
                scam_penalty = min(50, row.report_count * 10)
                entity.aggregate_score = max(0, (entity.aggregate_score or 50) - scam_penalty)
                await db.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def blockchain_sync(self):
    """
    Blockchain sync workflow:
    1. Pull entities where on_chain=FALSE and verdict=HIGH_RISK
    2. Submit flagEntity() transactions in batches of 10
    3. Update entities.on_chain = TRUE, save tx_hash
    """
    logger.info("workflow.blockchain_sync.started")
    try:
        asyncio.run(_async_blockchain_sync())
        logger.info("workflow.blockchain_sync.completed")
        return {"status": "completed"}
    except Exception as exc:
        logger.error("workflow.blockchain_sync.error", error=str(exc))
        raise self.retry(exc=exc)


async def _async_blockchain_sync():
    """Async implementation of blockchain sync."""
    from app.models.database import AsyncSessionLocal
    from app.models.postgres import Entity, Investigation
    from app.services.blockchain import BlockchainService
    from sqlalchemy import select

    blockchain_service = BlockchainService()
    if not blockchain_service.enabled:
        logger.info("workflow.blockchain_sync.disabled")
        return

    async with AsyncSessionLocal() as db:
        # Find HIGH_RISK entities not on chain
        result = await db.execute(
            select(Entity).where(
                Entity.on_chain == False,
                Entity.aggregate_score < 25,
            ).limit(10)
        )
        entities = result.scalars().all()

        for entity in entities:
            try:
                tx_hash = await blockchain_service.flag_entity(
                    entity_type=entity.entity_type,
                    entity_value=entity.entity_value,
                    trust_score=entity.aggregate_score or 0,
                )
                if tx_hash:
                    entity.on_chain = True
                    await db.commit()
                    logger.info("blockchain_sync.flagged", entity=entity.entity_value, tx=tx_hash)
            except Exception as e:
                logger.error("blockchain_sync.failed", entity=entity.entity_value, error=str(e))
