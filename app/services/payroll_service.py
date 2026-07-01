import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payroll import Payslip, StaffProfile
from app.schemas.payroll import PayslipCreate, StaffProfileCreate, StaffProfileUpdate


async def list_staff(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    center_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[StaffProfile], int]:
    q = select(StaffProfile).where(
        StaffProfile.organization_id == org_id,
        StaffProfile.deleted_at.is_(None),
    )
    if center_id:
        q = q.where(StaffProfile.center_id == center_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(items), total


async def create_staff(db: AsyncSession, org_id: uuid.UUID, data: StaffProfileCreate) -> StaffProfile:
    staff = StaffProfile(organization_id=org_id, **data.model_dump(exclude={"phone", "email"}))
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


async def update_staff(
    db: AsyncSession, org_id: uuid.UUID, staff_id: uuid.UUID, data: StaffProfileUpdate
) -> StaffProfile:
    staff = await _get_staff(db, org_id, staff_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(staff, k, v)
    await db.commit()
    await db.refresh(staff)
    return staff


async def delete_staff(db: AsyncSession, org_id: uuid.UUID, staff_id: uuid.UUID) -> None:
    from datetime import datetime, timezone
    staff = await _get_staff(db, org_id, staff_id)
    staff.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def _get_staff(db: AsyncSession, org_id: uuid.UUID, staff_id: uuid.UUID) -> StaffProfile:
    result = await db.execute(
        select(StaffProfile).where(
            StaffProfile.id == staff_id,
            StaffProfile.organization_id == org_id,
            StaffProfile.deleted_at.is_(None),
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


async def create_payslip(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: PayslipCreate,
    created_by: uuid.UUID,
) -> Payslip:
    staff = await _get_staff(db, org_id, data.staff_id)
    # Check for duplicate
    existing = (
        await db.execute(
            select(Payslip).where(
                Payslip.staff_id == data.staff_id,
                Payslip.pay_period == data.pay_period,
                Payslip.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Payslip already exists for this period")

    basic = staff.basic_salary
    gross = basic + data.allowances + data.bonus
    net = gross - data.deductions

    payslip = Payslip(
        organization_id=org_id,
        staff_id=data.staff_id,
        pay_period=data.pay_period,
        basic_salary=basic,
        allowances=data.allowances,
        deductions=data.deductions,
        bonus=data.bonus,
        gross_pay=gross,
        net_pay=net,
        breakdown=data.breakdown,
        notes=data.notes,
        status="draft",
    )
    db.add(payslip)
    await db.commit()
    await db.refresh(payslip)
    return payslip


async def list_payslips(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    staff_id: uuid.UUID | None = None,
    pay_period: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Payslip], int]:
    q = select(Payslip).where(
        Payslip.organization_id == org_id,
        Payslip.deleted_at.is_(None),
    )
    if staff_id:
        q = q.where(Payslip.staff_id == staff_id)
    if pay_period:
        q = q.where(Payslip.pay_period == pay_period)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.order_by(Payslip.pay_period.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return list(items), total


async def approve_payslip(db: AsyncSession, org_id: uuid.UUID, payslip_id: uuid.UUID) -> Payslip:
    payslip = await _get_payslip(db, org_id, payslip_id)
    if payslip.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft payslips can be approved")
    payslip.status = "approved"
    await db.commit()
    await db.refresh(payslip)
    return payslip


async def mark_paid(db: AsyncSession, org_id: uuid.UUID, payslip_id: uuid.UUID) -> Payslip:
    from datetime import date
    payslip = await _get_payslip(db, org_id, payslip_id)
    if payslip.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved payslips can be marked paid")
    payslip.status = "paid"
    payslip.paid_at = date.today()
    await db.commit()
    await db.refresh(payslip)
    return payslip


async def _get_payslip(db: AsyncSession, org_id: uuid.UUID, payslip_id: uuid.UUID) -> Payslip:
    result = await db.execute(
        select(Payslip).where(
            Payslip.id == payslip_id,
            Payslip.organization_id == org_id,
            Payslip.deleted_at.is_(None),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Payslip not found")
    return p
