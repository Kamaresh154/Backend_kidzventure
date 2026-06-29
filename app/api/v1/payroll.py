from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import CurrentUserDep, DbSession
from app.schemas.payroll import (
    PayslipCreate, PayslipListResponse, PayslipResponse,
    StaffListResponse, StaffProfileCreate, StaffProfileResponse, StaffProfileUpdate,
)
from app.services import payroll_service

router = APIRouter(prefix="/payroll", tags=["payroll"])


def _require_org(current: CurrentUserDep) -> UUID:
    """Resolve org_id — super_admin must pass ?org_id=; others use their own."""
    if current.org_id is None:
        raise HTTPException(status_code=400, detail="No organization context. Super admin must specify org_id param.")
    return current.org_id


# ── Staff ──────────────────────────────────────────────────────────────────

@router.get("/staff", response_model=StaffListResponse)
async def list_staff(
    db: DbSession,
    current: CurrentUserDep,
    org_id: UUID | None = None,
    center_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StaffListResponse:
    current.require_permission("payroll.read")
    # super_admin can pass explicit org_id; others use their own
    if "super_admin" in current.roles:
        resolved = org_id or current.org_id
        if resolved is None:
            return StaffListResponse(items=[], total=0, page=page, page_size=page_size)
    else:
        resolved = _require_org(current)
    items, total = await payroll_service.list_staff(
        db, resolved, center_id=center_id, page=page, page_size=page_size
    )
    return StaffListResponse(items=[StaffProfileResponse.model_validate(s) for s in items], total=total, page=page, page_size=page_size)


@router.post("/staff", response_model=StaffProfileResponse, status_code=201)
async def create_staff(data: StaffProfileCreate, db: DbSession, current: CurrentUserDep) -> StaffProfileResponse:
    current.require_permission("payroll.write")
    resolved = _require_org(current)
    staff = await payroll_service.create_staff(db, resolved, data)
    return StaffProfileResponse.model_validate(staff)


@router.patch("/staff/{staff_id}", response_model=StaffProfileResponse)
async def update_staff(staff_id: UUID, data: StaffProfileUpdate, db: DbSession, current: CurrentUserDep) -> StaffProfileResponse:
    current.require_permission("payroll.write")
    resolved = _require_org(current)
    staff = await payroll_service.update_staff(db, resolved, staff_id, data)
    return StaffProfileResponse.model_validate(staff)


@router.delete("/staff/{staff_id}", status_code=204)
async def delete_staff(staff_id: UUID, db: DbSession, current: CurrentUserDep) -> None:
    current.require_permission("payroll.write")
    resolved = _require_org(current)
    await payroll_service.delete_staff(db, resolved, staff_id)


# ── Payslips ───────────────────────────────────────────────────────────────

@router.get("/payslips", response_model=PayslipListResponse)
async def list_payslips(
    db: DbSession,
    current: CurrentUserDep,
    staff_id: UUID | None = None,
    pay_period: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PayslipListResponse:
    current.require_permission("payroll.read")
    resolved = _require_org(current)
    items, total = await payroll_service.list_payslips(
        db, resolved, staff_id=staff_id, pay_period=pay_period, page=page, page_size=page_size
    )
    return PayslipListResponse(items=[PayslipResponse.model_validate(p) for p in items], total=total, page=page, page_size=page_size)


@router.post("/payslips", response_model=PayslipResponse, status_code=201)
async def create_payslip(data: PayslipCreate, db: DbSession, current: CurrentUserDep) -> PayslipResponse:
    current.require_permission("payroll.write")
    resolved = _require_org(current)
    payslip = await payroll_service.create_payslip(db, resolved, data, current.user.id)
    return PayslipResponse.model_validate(payslip)


@router.post("/payslips/{payslip_id}/approve", response_model=PayslipResponse)
async def approve_payslip(payslip_id: UUID, db: DbSession, current: CurrentUserDep) -> PayslipResponse:
    current.require_permission("payroll.write")
    resolved = _require_org(current)
    payslip = await payroll_service.approve_payslip(db, resolved, payslip_id)
    return PayslipResponse.model_validate(payslip)


@router.post("/payslips/{payslip_id}/mark-paid", response_model=PayslipResponse)
async def mark_paid(payslip_id: UUID, db: DbSession, current: CurrentUserDep) -> PayslipResponse:
    current.require_permission("payroll.write")
    resolved = _require_org(current)
    payslip = await payroll_service.mark_paid(db, resolved, payslip_id)
    return PayslipResponse.model_validate(payslip)
