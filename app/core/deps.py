from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


class CurrentUser:
    def __init__(
        self,
        user: User,
        roles: list[str],
        permissions: list[str],
        org_id: UUID | None,
    ):
        self.user = user
        self.roles = roles
        self.permissions = permissions
        self.org_id = org_id

    def has_permission(self, code: str) -> bool:
        if "super_admin" in self.roles:
            return True
        return code in self.permissions

    def require_permission(self, code: str) -> None:
        if not self.has_permission(code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {code}",
            )


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(
        select(User)
        .where(User.id == UUID(user_id), User.deleted_at.is_(None))
        .options(selectinload(User.user_roles))
    )
    user = result.scalar_one_or_none()
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    org_id = payload.get("org_id")
    parsed_org = UUID(org_id) if org_id else None

    roles = payload.get("roles", [])
    if parsed_org is None and "super_admin" in roles:
        from app.models.organization import Organization
        result = await db.execute(
            select(Organization)
            .where(Organization.deleted_at.is_(None))
            .order_by(Organization.created_at)
            .limit(1)
        )
        org = result.scalar_one_or_none()
        if org:
            parsed_org = org.id

    return CurrentUser(
        user=user,
        roles=roles,
        permissions=payload.get("permissions", []),
        org_id=parsed_org,
    )


async def resolve_org_id(current: CurrentUser, db: AsyncSession) -> UUID:
    if current.org_id is not None:
        return current.org_id
    if "super_admin" in current.roles:
        from app.models.organization import Organization
        result = await db.execute(
            select(Organization)
            .where(Organization.deleted_at.is_(None))
            .order_by(Organization.created_at)
            .limit(1)
        )
        org = result.scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=404, detail="No organization found")
        return org.id
    raise HTTPException(status_code=400, detail="No organization context")


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
