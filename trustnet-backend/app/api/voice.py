"""
Voice Investigation Router
POST /api/v1/voice - Submit audio for STT + investigation
"""

import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.investigate import (
    _check_dns,
    _check_mca,
    _check_phone,
    _check_safebrowsing,
    trust_engine,
    CategoryScorer,
)
from app.core.trust_engine import TrustEngine
from app.models.database import get_db
from app.models.postgres import Investigation
from app.models.schemas import (
    ErrorResponse,
    EvidenceItem,
    ExtractedEntities,
    VoiceInvestigationRequest,
    VoiceInvestigationResponse,
)
from app.services.mca_service import MCAService
from app.services.sarvam_service import SarvamService
from app.services.whois_service import WHOISService

router = APIRouter()
sarvam_service = SarvamService()
whois_service = WHOISService()


@router.post(
    "/voice",
    response_model=VoiceInvestigationResponse,
    status_code=status.HTTP_200_OK,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Submit audio for STT + investigation",
    description="Transcribes audio using Sarvam AI, then runs full investigation pipeline.",
)
async def voice_investigate(
    body: VoiceInvestigationRequest,
    db: AsyncSession = Depends(get_db),
) -> VoiceInvestigationResponse:
    """
    Voice investigation pipeline:
    1. Transcribe audio (Sarvam STT)
    2. Run investigation on transcript
    3. Return results with transcript
    """
    start_time = time.time()

    # Step 1: Transcribe audio
    try:
        transcript = await sarvam_service.transcribe_voice(
            body.audio_base64, body.mime_type
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(exc)}",
        )

    if not transcript or len(transcript.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Could not transcribe audio or transcription too short.",
        )

    # Step 2: Extract entities from transcript
    entities = await sarvam_service.extract_entities(transcript)

    # Step 3: Run verification (parallel)
    import asyncio

    mca_task = _check_mca(entities.get("company_name"), db)
    whois_task = _check_whois(entities.get("website_url"))
    dns_task = _check_dns(entities.get("email"))
    safebrowsing_task = _check_safebrowsing(entities.get("website_url"))

    results = await asyncio.gather(
        mca_task, whois_task, dns_task, safebrowsing_task,
        return_exceptions=True,
    )

    mca_result = results[0] if not isinstance(results[0], Exception) else {"found": False}
    whois_result = results[1] if not isinstance(results[1], Exception) else {"found": False}
    dns_result = results[2] if not isinstance(results[2], Exception) else {"checked": False}
    safebrowsing_result = results[3] if not isinstance(results[3], Exception) else {"checked": False, "flagged": False}

    # Step 4: Calculate trust score
    identity_score = CategoryScorer.score_identity_company(mca_result)
    domain_score = CategoryScorer.score_domain_infrastructure(
        whois_result, safebrowsing_result, {"checked": False}, {"checked": False}
    )
    comm_score = CategoryScorer.score_communication_channel(dns_result, entities.get("email"))
    content_score = CategoryScorer.score_content_red_flags(entities, transcript)
    community_score = CategoryScorer.score_community_intelligence({"flagged_count": 0, "rings": []}, [])

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
        "sarvam_extraction": True,
        "community_reports": False,
        "phone_verified": False,
        "email_auth": dns_result.get("checked", False),
    }

    trust_result = trust_engine.calculate(category_results, data_availability)

    # Step 5: Generate Hindi report
    hindi_report = await sarvam_service.generate_hindi_from_investigation({
        "verdict": trust_result["verdict"],
        "trust_score": trust_result["trust_score"],
        "evidence": trust_result["evidence"],
    })

    processing_ms = int((time.time() - start_time) * 1000)

    # Store investigation
    investigation = Investigation(
        raw_input=transcript,
        input_type="voice",
        entities_json=entities,
        trust_score=trust_result["trust_score"],
        confidence_score=trust_result["confidence_score"],
        verdict=trust_result["verdict"],
        category_scores_json=trust_result["category_scores"],
        evidence_json=trust_result["evidence"],
        hindi_explanation=hindi_report,
        processing_ms=processing_ms,
        fee_amount_inr=entities.get("fee_amount"),
        language_detected=entities.get("language_detected"),
    )
    db.add(investigation)
    await db.commit()
    await db.refresh(investigation)

    return VoiceInvestigationResponse(
        id=str(investigation.id),
        trust_score=trust_result["trust_score"],
        confidence_score=trust_result["confidence_score"],
        verdict=trust_result["verdict"],
        verdict_label=trust_result["verdict_label"],
        verdict_color=trust_result["verdict_color"],
        entities=ExtractedEntities(**entities),
        transcript=transcript,
        category_scores=trust_result["category_scores"],
        evidence=[EvidenceItem(**e) for e in trust_result["evidence"]],
        hindi_explanation=hindi_report,
        processing_ms=processing_ms,
        created_at=investigation.created_at,
    )
