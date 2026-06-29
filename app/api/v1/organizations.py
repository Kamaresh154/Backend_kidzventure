from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.deps import CurrentUserDep, DbSession
from app.models.organization import Organization
from app.schemas.organization import (
    CenterCreate,
    CenterResponse,
    CenterUpdate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _resolve_org_id(current: CurrentUserDep, org_id: UUID | None) -> UUID:
    if org_id is not None:
        if "super_admin" not in current.roles and current.org_id != org_id:
            raise HTTPException(status_code=403, detail="Cannot access this organization")
        return org_id
    if current.org_id is None:
        raise HTTPException(status_code=400, detail="No organization context")
    return current.org_id


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(current: CurrentUserDep, db: DbSession) -> OrganizationResponse:
    current.require_permission("organizations.read")
    # Super admin may have no org_id in JWT — return the first active org
    if current.org_id is None and "super_admin" in current.roles:
        result = await db.execute(
            select(Organization)
            .where(Organization.deleted_at.is_(None))
            .order_by(Organization.created_at)
            .limit(1)
        )
        org = result.scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=404, detail="No organization found")
        return OrganizationResponse.model_validate(org)
    org_id = _resolve_org_id(current, None)
    org = await organization_service.get_organization(db, org_id)
    return OrganizationResponse.model_validate(org)


@router.patch("/me", response_model=OrganizationResponse)
async def update_my_organization(
    data: OrganizationUpdate,
    current: CurrentUserDep,
    db: DbSession,
) -> OrganizationResponse:
    current.require_permission("organizations.write")
    org_id = _resolve_org_id(current, None)
    org = await organization_service.update_organization(db, org_id, data)
    return OrganizationResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    current: CurrentUserDep,
    db: DbSession,
) -> OrganizationResponse:
    current.require_permission("organizations.read")
    resolved = _resolve_org_id(current, org_id)
    org = await organization_service.get_organization(db, resolved)
    return OrganizationResponse.model_validate(org)


@router.get("/{org_id}/centers", response_model=list[CenterResponse])
async def list_centers(
    org_id: UUID,
    current: CurrentUserDep,
    db: DbSession,
) -> list[CenterResponse]:
    current.require_permission("centers.read")
    resolved = _resolve_org_id(current, org_id)
    centers = await organization_service.list_centers(db, resolved)
    return [CenterResponse.model_validate(c) for c in centers]


@router.post("/{org_id}/centers", response_model=CenterResponse, status_code=201)
async def create_center(
    org_id: UUID,
    data: CenterCreate,
    current: CurrentUserDep,
    db: DbSession,
) -> CenterResponse:
    current.require_permission("centers.write")
    resolved = _resolve_org_id(current, org_id)
    center = await organization_service.create_center(db, resolved, data)
    return CenterResponse.model_validate(center)


@router.get("/{org_id}/centers/{center_id}", response_model=CenterResponse)
async def get_center(
    org_id: UUID,
    center_id: UUID,
    current: CurrentUserDep,
    db: DbSession,
) -> CenterResponse:
    current.require_permission("centers.read")
    resolved = _resolve_org_id(current, org_id)
    center = await organization_service.get_center(db, resolved, center_id)
    return CenterResponse.model_validate(center)


@router.patch("/{org_id}/centers/{center_id}", response_model=CenterResponse)
async def update_center(
    org_id: UUID,
    center_id: UUID,
    data: CenterUpdate,
    current: CurrentUserDep,
    db: DbSession,
) -> CenterResponse:
    current.require_permission("centers.write")
    resolved = _resolve_org_id(current, org_id)
    center = await organization_service.update_center(db, resolved, center_id, data)
    return CenterResponse.model_validate(center)


@router.delete("/{org_id}/centers/{center_id}", status_code=204)
async def delete_center(
    org_id: UUID,
    center_id: UUID,
    current: CurrentUserDep,
    db: DbSession,
) -> None:
    current.require_permission("centers.write")
    resolved = _resolve_org_id(current, org_id)
    await organization_service.soft_delete_center(db, resolved, center_id)
