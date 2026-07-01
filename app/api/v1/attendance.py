from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, ResolvedOrgDep
from app.schemas.attendance import (
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceListResponse,
    AttendanceResponse,
    AttendanceSummary,
)
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("", response_model=AttendanceListResponse)
async def list_attendance(
    current: CurrentUserDep,
    db: DbSession,
    org_id: ResolvedOrgDep,
    center_id: UUID | None = None,
    student_id: UUID | None = None,
    on_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> AttendanceListResponse:
    current.require_permission("attendance.read")
    rows, total = await attendance_service.list_attendance(
        db,
        org_id,
        center_id=center_id,
        student_id=student_id,
        on_date=on_date,
        page=page,
        page_size=page_size,
    )
    items = [
        AttendanceResponse(
            id=rec.id,
            organization_id=rec.organization_id,
            center_id=rec.center_id,
            student_id=rec.student_id,
            student_name=name,
            check_in_at=rec.check_in_at,
            check_out_at=rec.check_out_at,
            method=rec.method,
            notes=rec.notes,
            created_at=rec.created_at,
        )
        for rec, name in rows
    ]
    return AttendanceListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary", response_model=AttendanceSummary)
async def attendance_summary(
    current: CurrentUserDep,
    db: DbSession,
    org_id: ResolvedOrgDep,
    center_id: UUID,
    on_date: date | None = None,
) -> AttendanceSummary:
    current.require_permission("attendance.read")
    target = on_date or date.today()
    return await attendance_service.daily_summary(db, org_id, center_id, target)


@router.post("/check-in", response_model=AttendanceResponse, status_code=201)
async def check_in(
    data: AttendanceCheckIn, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> AttendanceResponse:
    current.require_permission("attendance.write")
    record = await attendance_service.check_in(
        db, org_id, current.user.id, data
    )
    return AttendanceResponse(
        id=record.id,
        organization_id=record.organization_id,
        center_id=record.center_id,
        student_id=record.student_id,
        check_in_at=record.check_in_at,
        check_out_at=record.check_out_at,
        method=record.method,
        notes=record.notes,
        created_at=record.created_at,
    )


@router.post("/{record_id}/check-out", response_model=AttendanceResponse)
async def check_out(
    record_id: UUID,
    data: AttendanceCheckOut,
    current: CurrentUserDep,
    db: DbSession,
    org_id: ResolvedOrgDep,
) -> AttendanceResponse:
    current.require_permission("attendance.write")
    record = await attendance_service.check_out(db, org_id, record_id, data.notes)
    return AttendanceResponse(
        id=record.id,
        organization_id=record.organization_id,
        center_id=record.center_id,
        student_id=record.student_id,
        check_in_at=record.check_in_at,
        check_out_at=record.check_out_at,
        method=record.method,
        notes=record.notes,
        created_at=record.created_at,
    )
