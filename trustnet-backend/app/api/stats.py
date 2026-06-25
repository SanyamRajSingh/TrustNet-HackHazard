"""
Stats Router
GET /api/v1/stats - Platform statistics
GET /api/v1/entity/{hash} - Look up entity by hash
GET /api/v1/investigate/{id} - Retrieve investigation by ID
GET /api/v1/registry/check/{hash} - Query blockchain registry
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.postgres import Entity, Investigation, StatsCounter
from app.models.schemas import (
    BlockchainCheckResponse,
    EntityResponse,
    InvestigationDetail,
    StatsResponse,
)
from app.services.blockchain import BlockchainService

router = APIRouter()
blockchain_service = BlockchainService()


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Platform statistics",
)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsResponse:
    """Get platform statistics for counter animations."""
    # Total investigations
    inv_count_result = await db.execute(select(func.count(Investigation.id)))
    total_investigations = inv_count_result.scalar() or 0

    # Total entities flagged
    flagged_result = await db.execute(
        select(func.count(Entity.id)).where(
            Entity.aggregate_score < 25
        )
    )
    total_entities_flagged = flagged_result.scalar() or 0

    # On-chain records
    onchain_result = await db.execute(
        select(func.count(Entity.id)).where(Entity.on_chain == True)
    )
    total_on_chain = onchain_result.scalar() or 0

    # High risk percentage
    high_risk_result = await db.execute(
        select(func.count(Investigation.id)).where(
            Investigation.verdict == "HIGH_RISK"
        )
    )
    high_risk_count = high_risk_result.scalar() or 0
    high_risk_pct = (high_risk_count / total_investigations * 100) if total_investigations > 0 else 0

    # Average processing time
    avg_ms_result = await db.execute(
        select(func.avg(Investigation.processing_ms))
    )
    avg_ms = int(avg_ms_result.scalar() or 0)

    # INR protected (estimated: sum of fees in HIGH_RISK investigations)
    inr_result = await db.execute(
        select(func.sum(Investigation.fee_amount_inr)).where(
            Investigation.verdict == "HIGH_RISK"
        )
    )
    total_inr = inr_result.scalar() or 0

    return StatsResponse(
        total_investigations=total_investigations,
        total_entities_flagged=total_entities_flagged,
        total_inr_protected=total_inr,
        total_on_chain_records=total_on_chain,
        high_risk_percentage=round(high_risk_pct, 1),
        avg_processing_ms=avg_ms,
    )


@router.get(
    "/entity/{entity_hash}",
    response_model=EntityResponse,
    summary="Look up entity by hash",
)
async def get_entity(
    entity_hash: str,
    db: AsyncSession = Depends(get_db),
) -> EntityResponse:
    """Get entity details by SHA-256 hash."""
    result = await db.execute(
        select(Entity).where(Entity.entity_hash == entity_hash)
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return EntityResponse(
        id=str(entity.id),
        entity_type=entity.entity_type,
        entity_value=entity.entity_value,
        entity_hash=entity.entity_hash,
        first_seen_at=entity.first_seen_at,
        investigation_count=entity.investigation_count,
        aggregate_score=entity.aggregate_score,
        on_chain=entity.on_chain,
        ring_name=entity.ring_name,
    )


@router.get(
    "/investigate/{investigation_id}",
    response_model=InvestigationDetail,
    summary="Retrieve investigation result by ID",
)
async def get_investigation(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
) -> InvestigationDetail:
    """Get full investigation details by ID."""
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    from app.models.schemas import CategoryBreakdown, EvidenceItem, ExtractedEntities

    return InvestigationDetail(
        id=str(inv.id),
        trust_score=inv.trust_score or 0,
        confidence_score=inv.confidence_score or 0,
        verdict=inv.verdict,
        verdict_label=inv.verdict,
        verdict_color="",
        entities=ExtractedEntities(**(inv.entities_json or {})),
        category_scores=inv.category_scores_json or {},
        evidence=[EvidenceItem(**e) for e in (inv.evidence_json or [])],
        hindi_explanation=inv.hindi_explanation,
        graph_connections=inv.neo4j_connections_json,
        blockchain_tx_hash=inv.blockchain_tx_hash,
        processing_ms=inv.processing_ms or 0,
        created_at=inv.created_at,
        raw_input=inv.raw_input,
        input_type=inv.input_type,
    )


@router.get(
    "/registry/check/{entity_hash}",
    response_model=BlockchainCheckResponse,
    summary="Query Base blockchain registry",
)
async def check_registry(entity_hash: str) -> BlockchainCheckResponse:
    """Check if entity hash is recorded on Base blockchain."""
    result = await blockchain_service.check_entity("domain", entity_hash)

    return BlockchainCheckResponse(
        entity_hash=result.get("entity_hash", entity_hash),
        entity_type=result.get("entity_type", 0),
        trust_score=result.get("trust_score", 0),
        report_count=result.get("report_count", 0),
        first_flagged_at=result.get("first_flagged_at"),
        last_updated_at=result.get("last_updated_at"),
        is_active=result.get("is_active", False),
    )
