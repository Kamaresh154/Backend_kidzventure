from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, ResolvedOrgDep
from app.schemas.payroll import (
    PayslipCreate, PayslipListResponse, PayslipResponse,
    StaffListResponse, StaffProfileCreate, StaffProfileResponse, StaffProfileUpdate,
)
from app.services import payroll_service

router = APIRouter(prefix="/payroll", tags=["payroll"])


# ── Staff ──────────────────────────────────────────────────────────────────

@router.get("/staff", response_model=StaffListResponse)
async def list_staff(
    db: DbSession,
    current: CurrentUserDep,
    org_id: ResolvedOrgDep,
    center_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StaffListResponse:
    current.require_permission("payroll.read")
    items, total = await payroll_service.list_staff(
        db, org_id, center_id=center_id, page=page, page_size=page_size
    )
    return StaffListResponse(items=[StaffProfileResponse.model_validate(s) for s in items], total=total, page=page, page_size=page_size)


@router.post("/staff", response_model=StaffProfileResponse, status_code=201)
async def create_staff(data: StaffProfileCreate, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> StaffProfileResponse:
    current.require_permission("payroll.write")
    staff = await payroll_service.create_staff(db, org_id, data)
    return StaffProfileResponse.model_validate(staff)


@router.patch("/staff/{staff_id}", response_model=StaffProfileResponse)
async def update_staff(staff_id: UUID, data: StaffProfileUpdate, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> StaffProfileResponse:
    current.require_permission("payroll.write")
    staff = await payroll_service.update_staff(db, org_id, staff_id, data)
    return StaffProfileResponse.model_validate(staff)


@router.delete("/staff/{staff_id}", status_code=204)
async def delete_staff(staff_id: UUID, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> None:
    current.require_permission("payroll.write")
    await payroll_service.delete_staff(db, org_id, staff_id)


# ── Payslips ───────────────────────────────────────────────────────────────

@router.get("/payslips", response_model=PayslipListResponse)
async def list_payslips(
    db: DbSession,
    current: CurrentUserDep,
    org_id: ResolvedOrgDep,
    staff_id: UUID | None = None,
    pay_period: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PayslipListResponse:
    current.require_permission("payroll.read")
    items, total = await payroll_service.list_payslips(
        db, org_id, staff_id=staff_id, pay_period=pay_period, page=page, page_size=page_size
    )
    return PayslipListResponse(items=[PayslipResponse.model_validate(p) for p in items], total=total, page=page, page_size=page_size)


@router.post("/payslips", response_model=PayslipResponse, status_code=201)
async def create_payslip(data: PayslipCreate, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> PayslipResponse:
    current.require_permission("payroll.write")
    payslip = await payroll_service.create_payslip(db, org_id, data, current.user.id)
    return PayslipResponse.model_validate(payslip)


@router.post("/payslips/{payslip_id}/approve", response_model=PayslipResponse)
async def approve_payslip(payslip_id: UUID, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> PayslipResponse:
    current.require_permission("payroll.write")
    payslip = await payroll_service.approve_payslip(db, org_id, payslip_id)
    return PayslipResponse.model_validate(payslip)


@router.post("/payslips/{payslip_id}/mark-paid", response_model=PayslipResponse)
async def mark_paid(payslip_id: UUID, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> PayslipResponse:
    current.require_permission("payroll.write")
    payslip = await payroll_service.mark_paid(db, org_id, payslip_id)
    return PayslipResponse.model_validate(payslip)
