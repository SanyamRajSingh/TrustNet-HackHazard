"""
Health Router — extended service health checks.

GET /api/v1/health/sarvam   — Ping the Sarvam AI API (503 if down).
GET /api/v1/health/services — Quick status of all external services.
"""

import asyncio
from typing import Any, Dict

import structlog
from fastapi import APIRouter

from app.services.sarvam_service import SarvamService

logger = structlog.get_logger()
router = APIRouter(tags=["health"])

# Service singletons (reuse same instances as investigate.py)
_sarvam = SarvamService()


@router.get(
    "/health/sarvam",
    summary="Sarvam AI health check",
    description=(
        "Pings the Sarvam AI API. Returns 200 + model list when healthy, "
        "raises 503 when unreachable."
    ),
    responses={
        200: {"description": "Sarvam is reachable and key is valid"},
        503: {"description": "Sarvam is unreachable or key is invalid"},
    },
)
async def sarvam_health() -> Dict[str, Any]:
    """
    Ping the Sarvam AI API via GET /v1/models.
    Returns 200 {"status": "ok", "models": [...], "active_model": "sarvam-30b"}
    or raises 503 with the exact error reason.
    """
    result = await _sarvam.ping()
    logger.info("health.sarvam.ok", **result)
    return result


@router.get(
    "/health/services",
    summary="All external services health",
    description="Returns availability of all external services: Sarvam AI and Neo4j.",
)
async def services_health() -> Dict[str, Any]:
    """Quick status summary of all external service dependencies."""
    from app.services.neo4j_service import Neo4jService

    neo4j = Neo4jService()

    # Run checks in parallel — capture exceptions without crashing
    sarvam_result, neo4j_ok = await asyncio.gather(
        _sarvam.ping(),
        neo4j.verify_connectivity(),
        return_exceptions=True,
    )

    sarvam_status: Dict[str, Any]
    if isinstance(sarvam_result, Exception):
        sarvam_status = {"status": "error", "reason": str(sarvam_result)}
    else:
        sarvam_status = sarvam_result  # type: ignore[assignment]

    neo4j_status = (
        {"status": "ok"}
        if neo4j_ok is True
        else {"status": "error", "reason": str(neo4j_ok)}
    )

    all_ok = sarvam_status.get("status") == "ok" and neo4j_ok is True

    return {
        "overall": "ok" if all_ok else "degraded",
        "services": {
            "sarvam_ai": sarvam_status,
            "neo4j":     neo4j_status,
        },
    }
