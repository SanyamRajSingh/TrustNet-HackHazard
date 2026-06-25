"""
Investigation Router
POST /api/v1/investigate - Main investigation endpoint
"""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.trust_engine import CategoryScorer, TrustEngine, VERDICT_CONFIG
from app.models.database import get_db
from app.models.postgres import Entity, Investigation, StatsCounter
from app.models.schemas import (
    ErrorResponse,
    EvidenceItem,
    ExtractedEntities,
    InvestigationRequest,
    InvestigationResponse,
)
from app.services.blockchain import BlockchainService
from app.services.mca_service import MCAService
from app.services.neo4j_service import Neo4jService
from app.services.phone_service import PhoneService
from app.services.safebrowsing import PhishTankService, SafeBrowsingService, URLhausService
from app.services.sarvam_service import SarvamService
from app.services.whois_service import DNSAuthService, WHOISService

try:
    from neo4j.time import DateTime as Neo4jDateTime, Date as Neo4jDate
except ImportError:
    Neo4jDateTime = type("Neo4jDateTime", (), {})
    Neo4jDate = type("Neo4jDate", (), {})

def sanitize_for_json(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (Neo4jDateTime, Neo4jDate)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    return obj


router = APIRouter()

# Initialize services
trust_engine = TrustEngine()
sarvam_service = SarvamService()
whois_service = WHOISService()
dns_service = DNSAuthService()
safebrowsing_service = SafeBrowsingService()
phishtank_service = PhishTankService()
urlhaus_service = URLhausService()
phone_service = PhoneService()
neo4j_service = Neo4jService()
blockchain_service = BlockchainService()


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Submit text/screenshot/PDF for investigation",
    description="Main investigation endpoint. Accepts raw job offer text, analyzes it, and returns trust score.",
)
async def investigate(
    request: Request,
    body: InvestigationRequest,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """
    Main investigation pipeline:
    1. Extract entities (Sarvam AI)
    2. Run parallel verification (MCA, WHOIS, DNS, Safe Browsing, etc.)
    3. Query Neo4j graph
    4. Calculate trust score
    5. Generate Hindi report
    6. Return results
    """
    start_time = time.time()

    # Validate input
    if not body.raw_input or len(body.raw_input.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Input too short. Please provide the complete job offer text.",
        )

    # Step 1: Entity Extraction (Sarvam AI)
    entities = await sarvam_service.extract_entities(
        body.raw_input, body.source_language
    )

    # Step 2: Parallel verification calls
    mca_task = _check_mca(entities.get("company_name"), db)
    whois_task = _check_whois(entities.get("website_url"))
    dns_task = _check_dns(entities.get("email"))
    safebrowsing_task = _check_safebrowsing(entities.get("website_url"))
    phishtank_task = _check_phishtank(entities.get("website_url"))
    urlhaus_task = _check_urlhaus(entities.get("website_url"))
    phone_task = _check_phone(entities.get("phone_number"))

    # Execute all in parallel
    results = await asyncio.gather(
        mca_task, whois_task, dns_task,
        safebrowsing_task, phishtank_task, urlhaus_task, phone_task,
        return_exceptions=True,
    )

    mca_result = results[0] if not isinstance(results[0], Exception) else {"found": False}
    whois_result = results[1] if not isinstance(results[1], Exception) else {"found": False}
    dns_result = results[2] if not isinstance(results[2], Exception) else {"checked": False}
    safebrowsing_result = results[3] if not isinstance(results[3], Exception) else {"checked": False, "flagged": False}
    phishtank_result = results[4] if not isinstance(results[4], Exception) else {"checked": False, "flagged": False}
    urlhaus_result = results[5] if not isinstance(results[5], Exception) else {"checked": False, "flagged": False}
    phone_result = results[6] if not isinstance(results[6], Exception) else {"valid": False}

    # Step 3: Neo4j graph query
    ring_connections = {"flagged_count": 0, "rings": [], "nodes": [], "relationships": []}
    if entities.get("website_url"):
        try:
            domain = entities["website_url"].lower().replace("https://", "").replace("http://", "").split("/")[0]
            r_conn, r_graph = await asyncio.gather(
                neo4j_service.detect_ring_connections(domain),
                neo4j_service.get_entity_graph(domain, max_level=3),
                return_exceptions=True
            )
            if not isinstance(r_conn, Exception):
                ring_connections.update(r_conn)
            if not isinstance(r_graph, Exception):
                ring_connections.update(r_graph)
        except Exception:
            pass

    # Step 4: Trust Engine - Calculate scores
    identity_score = CategoryScorer.score_identity_company(mca_result)
    domain_score = CategoryScorer.score_domain_infrastructure(
        whois_result, safebrowsing_result, phishtank_result, urlhaus_result
    )
    comm_score = CategoryScorer.score_communication_channel(
        dns_result, entities.get("email")
    )
    content_score = CategoryScorer.score_content_red_flags(
        entities, body.raw_input
    )
    community_score = CategoryScorer.score_community_intelligence(
        ring_connections, []
    )

    category_results = {
        "identity_company": identity_score,
        "domain_infrastructure": domain_score,
        "communication_channel": comm_score,
        "content_red_flags": content_score,
        "community_intelligence": community_score,
    }

    data_availability = {
        "company_found": mca_result.get("found", False),
        "whois_data": whois_result.get("found", False),
        "dns_records": dns_result.get("checked", False),
        "sarvam_extraction": bool(entities.get("company_name") or entities.get("email") or entities.get("website_url")),
        "community_reports": False,  # TODO: query community reports
        "phone_verified": phone_result.get("valid", False),
        "email_auth": dns_result.get("checked", False),
    }

    trust_result = trust_engine.calculate(category_results, data_availability)

    # Step 4.5: Apply manual +15 risk penalty if known scam ring match
    if ring_connections.get("flagged_count", 0) > 0 or ring_connections.get("rings"):
        trust_result["trust_score"] = max(0, trust_result["trust_score"] - 15)
        # Update verdict based on new score
        if trust_result["trust_score"] < 25:
            trust_result["verdict"] = "HIGH_RISK"
        elif trust_result["trust_score"] < 45:
            trust_result["verdict"] = "SUSPICIOUS"
        elif trust_result["trust_score"] < 65:
            trust_result["verdict"] = "UNVERIFIED"
        
        verdict_conf = VERDICT_CONFIG.get(trust_result["verdict"], VERDICT_CONFIG["UNVERIFIED"])
        trust_result["verdict_label"] = verdict_conf["label"]
        trust_result["verdict_color"] = verdict_conf["color"]
        trust_result["evidence"].insert(0, {
            "category": "Community Intelligence",
            "finding": "15-point penalty applied for known Scam Ring match",
            "severity": "critical",
            "details": f"Matched rings: {', '.join(ring_connections.get('rings', []))}"
        })

    # Step 5: Generate Hindi report
    hindi_report = await sarvam_service.generate_hindi_from_investigation(
        trust_score=trust_result["trust_score"],
        verdict=trust_result["verdict"],
        key_findings=trust_result.get("evidence", []),
        entities=entities,
    )

    # Calculate processing time
    processing_ms = int((time.time() - start_time) * 1000)

    # Step 6: Store investigation
    investigation = Investigation(
        raw_input=body.raw_input,
        input_type=body.input_type,
        entities_json=sanitize_for_json(entities),
        trust_score=trust_result["trust_score"],
        confidence_score=trust_result["confidence_score"],
        verdict=trust_result["verdict"],
        category_scores_json=trust_result["category_scores"],
        evidence_json=sanitize_for_json(trust_result["evidence"]),
        hindi_explanation=hindi_report,
        neo4j_connections_json=sanitize_for_json(ring_connections),
        processing_ms=processing_ms,
        fee_amount_inr=entities.get("fee_amount"),
        language_detected=entities.get("language_detected"),
    )
    db.add(investigation)
    await db.commit()
    await db.refresh(investigation)

    # Step 7: Upsert to Neo4j graph (non-blocking)
    if trust_result["confidence_score"] >= 25:
        try:
            await neo4j_service.upsert_entities_from_investigation(
                entities,
                trust_result["trust_score"],
                str(investigation.id),
            )
        except Exception:
            pass

    # Step 8: Queue blockchain write if HIGH_RISK
    blockchain_tx = None
    if trust_result["verdict"] == "HIGH_RISK" and entities.get("website_url"):
        try:
            blockchain_tx = await blockchain_service.flag_entity(
                entity_type="domain",
                entity_value=entities["website_url"],
                trust_score=trust_result["trust_score"],
            )
        except Exception:
            pass

    # Step 9: Upsert entity record
    if entities.get("website_url"):
        entity_hash = hashlib.sha256(
            f"domain:{entities['website_url']}".encode()
        ).hexdigest()
        # Upsert entity (simplified - full implementation would check existing)
        entity = Entity(
            entity_type="domain",
            entity_value=entities["website_url"],
            entity_hash=entity_hash,
            aggregate_score=trust_result["trust_score"],
            on_chain=bool(blockchain_tx),
            ring_name=ring_connections["rings"][0] if ring_connections["rings"] else None,
        )
        db.add(entity)
        await db.commit()

    # Build response
    return InvestigationResponse(
        id=str(investigation.id),
        trust_score=trust_result["trust_score"],
        confidence_score=trust_result["confidence_score"],
        verdict=trust_result["verdict"],
        verdict_label=trust_result["verdict_label"],
        verdict_color=trust_result["verdict_color"],
        entities=ExtractedEntities(**entities),
        category_scores=trust_result["category_scores"],
        evidence=[EvidenceItem(**e) for e in trust_result["evidence"]],
        hindi_explanation=hindi_report,
        graph_connections=ring_connections,
        blockchain_tx_hash=blockchain_tx,
        processing_ms=processing_ms,
        created_at=investigation.created_at,
    )


# ============== Helper async functions ==============

async def _check_mca(company_name: Optional[str], db: AsyncSession):
    if not company_name:
        return {"found": False}
    service = MCAService(db=db)
    return await service.lookup_company(company_name)


async def _check_whois(domain: Optional[str]):
    from config import settings
    if not domain:
        return {"found": False, "checked": False}
    if not settings.WHOIS_API_KEY:
        import structlog
        structlog.get_logger().warning("skipping_whois_check", reason="WHOIS_API_KEY not set")
        return {"found": False, "checked": False, "skipped": True}
    return await whois_service.lookup_domain(domain)


async def _check_dns(email: Optional[str]):
    if not email or "@" not in email:
        return {"checked": False}
    domain = email.split("@")[-1]
    return await dns_service.check_email_auth(domain)


async def _check_safebrowsing(url: Optional[str]):
    from config import settings
    if not url:
        return {"checked": False, "flagged": False}
    if not settings.GOOGLE_SAFE_BROWSING_KEY:
        import structlog
        structlog.get_logger().warning("skipping_safebrowsing_check", reason="GOOGLE_SAFE_BROWSING_KEY not set")
        return {"checked": False, "flagged": False, "skipped": True}
    return await safebrowsing_service.check_url(url)


async def _check_phishtank(url: Optional[str]):
    if not url:
        return {"checked": False, "flagged": False}
    return await phishtank_service.check_url(url)


async def _check_urlhaus(url: Optional[str]):
    if not url:
        return {"checked": False, "flagged": False}
    return await urlhaus_service.check_url(url)


async def _check_phone(phone: Optional[str]):
    from config import settings
    if not phone:
        return {"valid": False}
    if not settings.NUMVERIFY_API_KEY:
        import structlog
        structlog.get_logger().warning("skipping_phone_check", reason="NUMVERIFY_API_KEY not set")
        return {"valid": False, "checked": False, "skipped": True}
    return await phone_service.verify_phone(phone)