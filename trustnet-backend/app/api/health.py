"""
Health Router — extended service health checks.

GET /api/v1/health/sarvam  — Ping the Sarvam AI API.
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
        "Pings the Sarvam AI API and returns its availability status. "
        "Use this for monitoring dashboards."
    ),
    responses={
        200: {
            "description": "Health status",
            "content": {
                "application/json": {
                    "examples": {
                        "ok":      {"value": {"status": "ok"}},
                        "degraded": {
                            "value": {
                                "status":   "degraded",
                                "fallback": True,
                                "reason":   "timeout",
                            }
                        },
                    }
                }
            },
        }
    },
)
async def sarvam_health() -> Dict[str, Any]:
    """
    Ping the Sarvam AI API.

    Returns:
      - `{"status": "ok"}` when the API responds successfully.
      - `{"status": "degraded", "fallback": true, "reason": "..."}` otherwise.
    """
    result = await _sarvam.ping()
    logger.info("health.sarvam", **result)
    return result


@router.get(
    "/health/services",
    summary="All external services health",
    description="Returns availability of all external services: Sarvam, Neo4j, Redis.",
)
async def services_health() -> Dict[str, Any]:
    """Quick status summary of all external service dependencies."""
    from app.services.neo4j_service import Neo4jService

    neo4j   = Neo4jService()

    # Run checks in parallel
    sarvam_result, neo4j_ok = await asyncio.gather(
        _sarvam.ping(),
        neo4j.verify_connectivity(),
        return_exceptions=True,
    )

    if isinstance(sarvam_result, Exception):
        sarvam_result = {"status": "degraded", "fallback": True, "reason": str(sarvam_result)}
    if isinstance(neo4j_ok, Exception):
        neo4j_ok = False

    all_ok = (
        sarvam_result.get("status") == "ok"
        and neo4j_ok is True
    )

    return {
        "overall":  "ok" if all_ok else "degraded",
        "services": {
            "sarvam_ai": sarvam_result,
            "neo4j":     {"status": "ok" if neo4j_ok else "degraded"},
        },
    }
