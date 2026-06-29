from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, resolve_org_id
from app.schemas.student import StudentCreate, StudentListResponse, StudentResponse, StudentUpdate
from app.services import student_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=StudentListResponse)
async def list_students(
    current: CurrentUserDep,
    db: DbSession,
    center_id: UUID | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StudentListResponse:
    current.require_permission("students.read")
    org_id = await resolve_org_id(current, db)
    items, total = await student_service.list_students(
        db, org_id, center_id=center_id, search=search, page=page, page_size=page_size,
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return StudentListResponse(
        items=[StudentResponse.model_validate(s) for s in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=StudentResponse, status_code=201)
async def create_student(
    data: StudentCreate, current: CurrentUserDep, db: DbSession,
) -> StudentResponse:
    current.require_permission("students.write")
    org_id = await resolve_org_id(current, db)
    student = await student_service.create_student(db, org_id, data)
    return StudentResponse.model_validate(student)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: UUID, current: CurrentUserDep, db: DbSession,
) -> StudentResponse:
    current.require_permission("students.read")
    org_id = await resolve_org_id(current, db)
    student = await student_service.get_student(db, org_id, student_id)
    return StudentResponse.model_validate(student)


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: UUID, data: StudentUpdate, current: CurrentUserDep, db: DbSession,
) -> StudentResponse:
    current.require_permission("students.write")
    org_id = await resolve_org_id(current, db)
    student = await student_service.update_student(db, org_id, student_id, data)
    return StudentResponse.model_validate(student)


@router.delete("/{student_id}", status_code=204)
async def delete_student(
    student_id: UUID, current: CurrentUserDep, db: DbSession,
) -> None:
    current.require_permission("students.write")
    org_id = await resolve_org_id(current, db)
    await student_service.soft_delete_student(db, org_id, student_id)
