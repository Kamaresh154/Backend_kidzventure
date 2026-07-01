from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, ResolvedOrgDep
from app.schemas.emp_attendance import (
    EmpAttendanceCheckOut, EmpAttendanceCreate, EmpAttendanceListResponse, EmpAttendanceResponse,
)
from app.services import emp_attendance_service

router = APIRouter(prefix="/attendance/emp", tags=["employee attendance"])


@router.get("", response_model=EmpAttendanceListResponse)
async def list_emp_attendance(
    db: DbSession,
    current: CurrentUserDep,
    org_id: ResolvedOrgDep,
    employee_id: UUID | None = None,
    on_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> EmpAttendanceListResponse:
    current.require_permission("payroll.read")
    items, total = await emp_attendance_service.list_attendance(
        db, org_id, employee_id=employee_id, on_date=on_date, page=page, page_size=page_size
    )
    return EmpAttendanceListResponse(items=[EmpAttendanceResponse.model_validate(i) for i in items], total=total, page=page, page_size=page_size)


@router.post("/check-in", response_model=EmpAttendanceResponse, status_code=201)
async def emp_check_in(data: EmpAttendanceCreate, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> EmpAttendanceResponse:
    current.require_permission("payroll.write")
    record = await emp_attendance_service.check_in(db, org_id, data)
    return EmpAttendanceResponse.model_validate(record)


@router.post("/check-out", response_model=EmpAttendanceResponse)
async def emp_check_out(
    employee_id: UUID,
    date_str: date,
    data: EmpAttendanceCheckOut,
    db: DbSession,
    current: CurrentUserDep,
    org_id: ResolvedOrgDep,
) -> EmpAttendanceResponse:
    current.require_permission("payroll.write")
    record = await emp_attendance_service.check_out(db, org_id, employee_id, date_str, data)
    return EmpAttendanceResponse.model_validate(record)


@router.get("/today/{employee_id}", response_model=EmpAttendanceResponse | None)
async def get_today_status(employee_id: UUID, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> EmpAttendanceResponse | None:
    current.require_permission("payroll.read")
    record = await emp_attendance_service.get_today_status(db, org_id, employee_id)
    if record:
        return EmpAttendanceResponse.model_validate(record)
    return None
