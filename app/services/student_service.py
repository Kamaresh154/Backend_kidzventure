import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Center
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate


def _generate_qr_code() -> str:
    return f"KV-{secrets.token_hex(8).upper()}"


async def list_students(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    center_id: uuid.UUID | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Student], int]:
    query = select(Student).where(
        Student.organization_id == org_id,
        Student.deleted_at.is_(None),
    )
    if center_id:
        query = query.where(Student.center_id == center_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            Student.full_name.ilike(term) | Student.admission_no.ilike(term)
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = (
        query.order_by(Student.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_student(db: AsyncSession, org_id: uuid.UUID, student_id: uuid.UUID) -> Student:
    result = await db.execute(
        select(Student).where(
            Student.id == student_id,
            Student.organization_id == org_id,
            Student.deleted_at.is_(None),
        )
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


async def create_student(db: AsyncSession, org_id: uuid.UUID, data: StudentCreate) -> Student:
    center_result = await db.execute(
        select(Center).where(
            Center.id == data.center_id,
            Center.organization_id == org_id,
            Center.deleted_at.is_(None),
        )
    )
    if center_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Invalid center for this organization")

    if data.admission_no:
        dup = await db.execute(
            select(Student).where(
                Student.organization_id == org_id,
                Student.admission_no == data.admission_no,
                Student.deleted_at.is_(None),
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Admission number already exists")

    student = Student(
        organization_id=org_id,
        center_id=data.center_id,
        batch_id=data.batch_id,
        admission_no=data.admission_no,
        full_name=data.full_name,
        dob=data.dob,
        gender=data.gender,
        medical_notes=data.medical_notes,
        qr_code=_generate_qr_code(),
        status="active",
    )
    db.add(student)
    await db.flush()
    return student


async def update_student(
    db: AsyncSession, org_id: uuid.UUID, student_id: uuid.UUID, data: StudentUpdate
) -> Student:
    student = await get_student(db, org_id, student_id)

    if data.center_id is not None:
        center_result = await db.execute(
            select(Center).where(
                Center.id == data.center_id,
                Center.organization_id == org_id,
                Center.deleted_at.is_(None),
            )
        )
        if center_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="Invalid center")
        student.center_id = data.center_id

    for field in ("full_name", "admission_no", "dob", "gender", "batch_id", "medical_notes", "status"):
        value = getattr(data, field)
        if value is not None:
            setattr(student, field, value)

    return student


async def soft_delete_student(
    db: AsyncSession, org_id: uuid.UUID, student_id: uuid.UUID
) -> None:
    student = await get_student(db, org_id, student_id)
    student.deleted_at = datetime.now(timezone.utc)
