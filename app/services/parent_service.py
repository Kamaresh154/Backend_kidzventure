import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Parent, Student, StudentParent
from app.schemas.parent import ParentCreate, ParentLinkRequest, ParentUpdate


async def list_parents(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Parent], int]:
    query = select(Parent).where(
        Parent.organization_id == org_id,
        Parent.deleted_at.is_(None),
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            Parent.full_name.ilike(term)
            | Parent.email.ilike(term)
            | Parent.phone.ilike(term)
        )
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(
        query.order_by(Parent.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_parent(db: AsyncSession, org_id: uuid.UUID, parent_id: uuid.UUID) -> Parent:
    result = await db.execute(
        select(Parent).where(
            Parent.id == parent_id,
            Parent.organization_id == org_id,
            Parent.deleted_at.is_(None),
        )
    )
    parent = result.scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


async def get_parent_students(
    db: AsyncSession, org_id: uuid.UUID, parent_id: uuid.UUID
) -> list[dict]:
    await get_parent(db, org_id, parent_id)
    result = await db.execute(
        select(Student, StudentParent)
        .join(StudentParent, StudentParent.student_id == Student.id)
        .where(
            StudentParent.parent_id == parent_id,
            Student.organization_id == org_id,
            Student.deleted_at.is_(None),
        )
    )
    return [
        {
            "id": student.id,
            "full_name": student.full_name,
            "admission_no": student.admission_no,
            "relationship": link.relationship,
            "is_primary": link.is_primary,
        }
        for student, link in result.all()
    ]


async def create_parent(db: AsyncSession, org_id: uuid.UUID, data: ParentCreate) -> Parent:
    parent = Parent(
        organization_id=org_id,
        full_name=data.full_name,
        phone=data.phone,
        email=str(data.email) if data.email else None,
    )
    db.add(parent)
    await db.flush()
    return parent


async def update_parent(
    db: AsyncSession, org_id: uuid.UUID, parent_id: uuid.UUID, data: ParentUpdate
) -> Parent:
    parent = await get_parent(db, org_id, parent_id)
    if data.full_name is not None:
        parent.full_name = data.full_name
    if data.phone is not None:
        parent.phone = data.phone
    if data.email is not None:
        parent.email = str(data.email)
    return parent


async def soft_delete_parent(db: AsyncSession, org_id: uuid.UUID, parent_id: uuid.UUID) -> None:
    parent = await get_parent(db, org_id, parent_id)
    parent.deleted_at = datetime.now(timezone.utc)


async def link_student(
    db: AsyncSession, org_id: uuid.UUID, parent_id: uuid.UUID, data: ParentLinkRequest
) -> StudentParent:
    await get_parent(db, org_id, parent_id)
    student_result = await db.execute(
        select(Student).where(
            Student.id == data.student_id,
            Student.organization_id == org_id,
            Student.deleted_at.is_(None),
        )
    )
    if student_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Student not found")

    existing = await db.execute(
        select(StudentParent).where(
            StudentParent.student_id == data.student_id,
            StudentParent.parent_id == parent_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Parent already linked to this student")

    if data.is_primary:
        existing_links = (
            await db.execute(
                select(StudentParent).where(StudentParent.student_id == data.student_id)
            )
        ).scalars().all()
        for link in existing_links:
            link.is_primary = False

    link = StudentParent(
        student_id=data.student_id,
        parent_id=parent_id,
        relationship=data.relationship,
        is_primary=data.is_primary,
    )
    db.add(link)
    await db.flush()
    return link


async def unlink_student(
    db: AsyncSession, org_id: uuid.UUID, parent_id: uuid.UUID, student_id: uuid.UUID
) -> None:
    await get_parent(db, org_id, parent_id)
    result = await db.execute(
        select(StudentParent).where(
            StudentParent.parent_id == parent_id,
            StudentParent.student_id == student_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.execute(
        delete(StudentParent).where(
            StudentParent.parent_id == parent_id,
            StudentParent.student_id == student_id,
        )
    )
