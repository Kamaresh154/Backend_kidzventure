from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import CurrentUserDep, DbSession
from app.services import franchise_service

router = APIRouter(prefix="/franchise", tags=["franchise"])


@router.get("/organizations")
async def list_all_organizations(
    db: DbSession,
    current: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict:
    if "super_admin" not in current.roles:
        raise HTTPException(status_code=403, detail="Super admin only")
    items, total = await franchise_service.list_all_organizations(db, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/organizations/{org_id}/stats")
async def get_org_stats(org_id: UUID, db: DbSession, current: CurrentUserDep) -> dict:
    # Super admin can view any; franchise_owner only their own
    if "super_admin" not in current.roles:
        if current.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")
    return await franchise_service.get_org_stats(db, org_id)


@router.get("/summary")
async def cross_franchise_summary(db: DbSession, current: CurrentUserDep) -> dict:
    if "super_admin" not in current.roles:
        raise HTTPException(status_code=403, detail="Super admin only")
    return await franchise_service.get_cross_franchise_summary(db)
