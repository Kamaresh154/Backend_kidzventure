from datetime import datetime

from fastapi import APIRouter, Query
from uuid import UUID

from app.core.deps import CurrentUserDep, DbSession
from app.services import reports_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/pl")
async def pl_report(
    db: DbSession,
    current: CurrentUserDep,
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
) -> dict:
    current.require_permission("reports.read")
    return await reports_service.get_pl_report(db, current.org_id, from_date, to_date)


@router.get("/balance-sheet")
async def balance_sheet(
    db: DbSession,
    current: CurrentUserDep,
    as_of: datetime = Query(default_factory=datetime.utcnow),
) -> dict:
    current.require_permission("reports.read")
    return await reports_service.get_balance_sheet(db, current.org_id, as_of)


@router.get("/gst")
async def gst_report(
    db: DbSession,
    current: CurrentUserDep,
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
) -> dict:
    current.require_permission("reports.read")
    return await reports_service.get_gst_report(db, current.org_id, from_date, to_date)


@router.get("/attendance-trend")
async def attendance_trend(
    db: DbSession,
    current: CurrentUserDep,
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
    center_id: UUID | None = None,
) -> list:
    current.require_permission("reports.read")
    return await reports_service.get_attendance_trend(db, current.org_id, from_date, to_date, center_id)


@router.get("/enrolment-trend")
async def enrolment_trend(
    db: DbSession,
    current: CurrentUserDep,
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
) -> list:
    current.require_permission("reports.read")
    return await reports_service.get_enrolment_trend(db, current.org_id, from_date, to_date)


@router.get("/revenue-trend")
async def revenue_trend(
    db: DbSession,
    current: CurrentUserDep,
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
) -> list:
    current.require_permission("reports.read")
    return await reports_service.get_revenue_trend(db, current.org_id, from_date, to_date)
