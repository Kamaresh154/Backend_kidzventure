import uuid
from datetime import date, datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceRecord
from app.models.organization import Center
from app.models.student import Student
from app.schemas.attendance import AttendanceCheckIn, AttendanceSummary


async def list_attendance(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    center_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    on_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[AttendanceRecord, str | None]], int]:
    query = (
        select(AttendanceRecord, Student.full_name)
        .join(Student, Student.id == AttendanceRecord.student_id)
        .where(AttendanceRecord.organization_id == org_id)
    )
    if center_id:
        query = query.where(AttendanceRecord.center_id == center_id)
    if student_id:
        query = query.where(AttendanceRecord.student_id == student_id)
    if on_date:
        start = datetime.combine(on_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(on_date, time.max, tzinfo=timezone.utc)
        query = query.where(
            AttendanceRecord.check_in_at >= start,
            AttendanceRecord.check_in_at <= end,
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(
        query.order_by(AttendanceRecord.check_in_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.all()), total


async def check_in(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: AttendanceCheckIn,
) -> AttendanceRecord:
    center_result = await db.execute(
        select(Center).where(
            Center.id == data.center_id,
            Center.organization_id == org_id,
            Center.deleted_at.is_(None),
        )
    )
    if center_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Invalid center")

    student: Student | None = None
    if data.student_id:
        result = await db.execute(
            select(Student).where(
                Student.id == data.student_id,
                Student.organization_id == org_id,
                Student.center_id == data.center_id,
                Student.deleted_at.is_(None),
            )
        )
        student = result.scalar_one_or_none()
    elif data.qr_code:
        result = await db.execute(
            select(Student).where(
                Student.qr_code == data.qr_code,
                Student.organization_id == org_id,
                Student.deleted_at.is_(None),
            )
        )
        student = result.scalar_one_or_none()
    else:
        raise HTTPException(status_code=400, detail="Provide student_id or qr_code")

    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    open_result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.check_out_at.is_(None),
        )
    )
    if open_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Student already checked in")

    now = datetime.now(timezone.utc)
    record = AttendanceRecord(
        organization_id=org_id,
        center_id=data.center_id,
        student_id=student.id,
        check_in_at=now,
        method=data.method,
        notes=data.notes,
        created_by=user_id,
        created_at=now,
    )
    db.add(record)
    await db.flush()
    return record


async def check_out(
    db: AsyncSession,
    org_id: uuid.UUID,
    record_id: uuid.UUID,
    notes: str | None = None,
) -> AttendanceRecord:
    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.id == record_id,
            AttendanceRecord.organization_id == org_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if record.check_out_at is not None:
        raise HTTPException(status_code=400, detail="Already checked out")

    record.check_out_at = datetime.now(timezone.utc)
    if notes:
        record.notes = notes
    return record


async def daily_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
    center_id: uuid.UUID,
    on_date: date,
) -> AttendanceSummary:
    start = datetime.combine(on_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(on_date, time.max, tzinfo=timezone.utc)

    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.organization_id == org_id,
            AttendanceRecord.center_id == center_id,
            AttendanceRecord.check_in_at >= start,
            AttendanceRecord.check_in_at <= end,
        )
    )
    records = list(result.scalars().all())
    checked_out = sum(1 for r in records if r.check_out_at is not None)
    return AttendanceSummary(
        date=on_date,
        present=len(records),
        checked_out=checked_out,
        still_in=len(records) - checked_out,
    )
