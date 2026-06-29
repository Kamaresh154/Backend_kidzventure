from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, resolve_org_id
from app.schemas.parent import (
    LinkedStudentBrief,
    ParentCreate,
    ParentDetailResponse,
    ParentLinkRequest,
    ParentListResponse,
    ParentResponse,
    ParentUpdate,
)
from app.services import parent_service

router = APIRouter(prefix="/parents", tags=["parents"])


@router.get("", response_model=ParentListResponse)
async def list_parents(
    current: CurrentUserDep,
    db: DbSession,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ParentListResponse:
    current.require_permission("parents.read")
    org_id = await resolve_org_id(current, db)
    items, total = await parent_service.list_parents(
        db, org_id, search=search, page=page, page_size=page_size
    )
    return ParentListResponse(
        items=[ParentResponse.model_validate(p) for p in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=ParentResponse, status_code=201)
async def create_parent(
    data: ParentCreate, current: CurrentUserDep, db: DbSession
) -> ParentResponse:
    current.require_permission("parents.write")
    org_id = await resolve_org_id(current, db)
    parent = await parent_service.create_parent(db, org_id, data)
    return ParentResponse.model_validate(parent)


@router.get("/{parent_id}", response_model=ParentDetailResponse)
async def get_parent(
    parent_id: UUID, current: CurrentUserDep, db: DbSession
) -> ParentDetailResponse:
    current.require_permission("parents.read")
    org_id = await resolve_org_id(current, db)
    parent = await parent_service.get_parent(db, org_id, parent_id)
    students = await parent_service.get_parent_students(db, org_id, parent_id)
    return ParentDetailResponse(
        **ParentResponse.model_validate(parent).model_dump(),
        students=[LinkedStudentBrief.model_validate(s) for s in students],
    )


@router.patch("/{parent_id}", response_model=ParentResponse)
async def update_parent(
    parent_id: UUID, data: ParentUpdate, current: CurrentUserDep, db: DbSession,
) -> ParentResponse:
    current.require_permission("parents.write")
    org_id = await resolve_org_id(current, db)
    parent = await parent_service.update_parent(db, org_id, parent_id, data)
    return ParentResponse.model_validate(parent)


@router.delete("/{parent_id}", status_code=204)
async def delete_parent(parent_id: UUID, current: CurrentUserDep, db: DbSession) -> None:
    current.require_permission("parents.write")
    org_id = await resolve_org_id(current, db)
    await parent_service.soft_delete_parent(db, org_id, parent_id)


@router.post("/{parent_id}/link", status_code=201)
async def link_student(
    parent_id: UUID, data: ParentLinkRequest, current: CurrentUserDep, db: DbSession,
) -> dict[str, str]:
    current.require_permission("parents.write")
    org_id = await resolve_org_id(current, db)
    await parent_service.link_student(db, org_id, parent_id, data)
    return {"message": "Linked"}


@router.delete("/{parent_id}/link/{student_id}", status_code=204)
async def unlink_student(
    parent_id: UUID, student_id: UUID, current: CurrentUserDep, db: DbSession
) -> None:
    current.require_permission("parents.write")
    org_id = await resolve_org_id(current, db)
    await parent_service.unlink_student(db, org_id, parent_id, student_id)
