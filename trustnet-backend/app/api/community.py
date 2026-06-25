"""
Community Reports Router
POST /api/v1/community/report - Submit community scam report
GET /api/v1/community/reports - List community reports
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.postgres import CommunityReport, Entity, User
from app.models.schemas import (
    CommunityReportRequest,
    CommunityReportResponse,
    ErrorResponse,
)

router = APIRouter()


@router.post(
    "/community/report",
    response_model=CommunityReportResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    summary="Submit community scam report",
)
async def submit_report(
    body: CommunityReportRequest,
    db: AsyncSession = Depends(get_db),
) -> CommunityReportResponse:
    """Submit a community report for an entity."""
    # Verify entity exists
    entity_result = await db.execute(
        select(Entity).where(Entity.id == body.entity_id)
    )
    entity = entity_result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    report = CommunityReport(
        entity_id=body.entity_id,
        reporter_user_id=None,  # Anonymous for now
        report_type=body.report_type,
        loss_amount_inr=body.loss_amount_inr,
        description=body.description,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return CommunityReportResponse(
        id=str(report.id),
        entity_id=str(report.entity_id),
        report_type=report.report_type,
        loss_amount_inr=report.loss_amount_inr,
        description=report.description,
        verified_by_admin=report.verified_by_admin,
        reporter_weight=float(report.reporter_weight),
        created_at=report.created_at,
    )


@router.get(
    "/community/reports",
    response_model=List[CommunityReportResponse],
    summary="List community reports",
)
async def list_reports(
    entity_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[CommunityReportResponse]:
    """List community reports, optionally filtered by entity."""
    query = select(CommunityReport).order_by(desc(CommunityReport.created_at)).limit(limit)
    if entity_id:
        query = query.where(CommunityReport.entity_id == entity_id)

    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        CommunityReportResponse(
            id=str(r.id),
            entity_id=str(r.entity_id),
            report_type=r.report_type,
            loss_amount_inr=r.loss_amount_inr,
            description=r.description,
            verified_by_admin=r.verified_by_admin,
            reporter_weight=float(r.reporter_weight),
            created_at=r.created_at,
        )
        for r in reports
    ]