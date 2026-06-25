"""
Voice Investigation Router
POST /api/v1/voice - Submit audio for STT + investigation
"""

import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.investigate import investigate
from app.core.trust_engine import TrustEngine
from app.models.database import get_db
from app.models.schemas import (
    ErrorResponse,
    InvestigationRequest,
    VoiceInvestigationRequest,
    VoiceInvestigationResponse,
)
from app.services.sarvam_service import SarvamService

router = APIRouter()
sarvam_service = SarvamService()


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

    # Step 2: Run standard investigation flow using transcript
    investigation_req = InvestigationRequest(
        raw_input=transcript,
        input_type="voice"
    )
    
    # We pass request=None because investigate does not actively use the Request object
    investigation_resp = await investigate(None, investigation_req, db)

    # Step 3: Bundle transcript into the standard response
    return VoiceInvestigationResponse(
        id=investigation_resp.id,
        trust_score=investigation_resp.trust_score,
        confidence_score=investigation_resp.confidence_score,
        verdict=investigation_resp.verdict,
        verdict_label=investigation_resp.verdict_label,
        verdict_color=investigation_resp.verdict_color,
        entities=investigation_resp.entities,
        transcript=transcript,
        category_scores=investigation_resp.category_scores,
        evidence=investigation_resp.evidence,
        hindi_explanation=investigation_resp.hindi_explanation,
        processing_ms=investigation_resp.processing_ms,
        created_at=investigation_resp.created_at,
        graph_connections=investigation_resp.graph_connections,
        blockchain_tx_hash=investigation_resp.blockchain_tx_hash,
    )
