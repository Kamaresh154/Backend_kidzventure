"""User management — super admin creates franchise & employee accounts."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from app.core.deps import CurrentUserDep, DbSession
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.services import auth_service
from sqlalchemy import select

router = APIRouter(prefix="/users", tags=["users"])

ALLOWED_ROLES = {"admin", "franchise_owner", "franchise_manager", "employee", "branch_manager", "accountant"}


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1)
    role: str = "employee"
    organization_id: UUID | None = None   # required for franchise_manager / employee


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=6)
    status: str | None = None
    role: str | None = None


class UserListItem(BaseModel):
    id: UUID
    email: str
    full_name: str
    status: str
    organization_id: UUID | None
    organization_name: str | None
    roles: list[str]

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int


@router.get("", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    current: CurrentUserDep,
    org_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> UserListResponse:
    """Super admin sees all users; franchise admin sees their own org users."""
    current.require_permission("users.read")

    q = select(User).where(User.deleted_at.is_(None))
    if "super_admin" in current.roles:
        if org_id:
            q = q.where(User.organization_id == org_id)
        # super admin: exclude other super admins from list
        # (handled on frontend via role filter)
    else:
        if current.org_id is None:
            return UserListResponse(items=[], total=0)
        q = q.where(User.organization_id == current.org_id)

    from sqlalchemy import func, select as sel
    count_q = sel(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()
    users = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    items = []
    for u in users:
        # load roles
        roles_res = await db.execute(
            select(Role).join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == u.id)
        )
        user_roles = [r.code for r in roles_res.scalars().all()]

        # load org name
        org_name = None
        if u.organization_id:
            org_res = await db.execute(select(Organization).where(Organization.id == u.organization_id))
            org = org_res.scalar_one_or_none()
            org_name = org.name if org else None

        items.append(UserListItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            status=u.status,
            organization_id=u.organization_id,
            organization_name=org_name,
            roles=user_roles,
        ))

    return UserListResponse(items=items, total=total)


@router.post("", status_code=201)
async def create_user(data: CreateUserRequest, db: DbSession, current: CurrentUserDep) -> UserListItem:
    """Super admin or franchise admin creates a user."""
    current.require_permission("users.write")

    role_code = data.role if data.role in ALLOWED_ROLES else "employee"

    # Determine org context
    if "super_admin" in current.roles:
        target_org_id = data.organization_id
    else:
        target_org_id = current.org_id
        # franchise admin can't create super_admin
        if role_code == "super_admin":
            raise HTTPException(403, "Cannot create super_admin")

    # Check email unique
    existing = (await db.execute(
        select(User).where(User.email == data.email.lower(), User.deleted_at.is_(None))
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Email already registered")

    # Verify org exists if specified
    if target_org_id:
        org = (await db.execute(select(Organization).where(Organization.id == target_org_id))).scalar_one_or_none()
        if not org:
            raise HTTPException(404, "Organization not found")

    user = User(
        organization_id=target_org_id,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        status="active",
    )
    db.add(user)
    await db.flush()

    role_obj = (await db.execute(select(Role).where(Role.code == role_code))).scalar_one_or_none()
    if role_obj:
        db.add(UserRole(
            user_id=user.id,
            role_id=role_obj.id,
            organization_id=target_org_id,
            center_id=None,
        ))

    await db.commit()
    await db.refresh(user)

    # Load org name
    org_name = None
    if user.organization_id:
        org_res = await db.execute(select(Organization).where(Organization.id == user.organization_id))
        org = org_res.scalar_one_or_none()
        org_name = org.name if org else None

    return UserListItem(
        id=user.id, email=user.email, full_name=user.full_name,
        status=user.status, organization_id=user.organization_id,
        organization_name=org_name, roles=[role_code],
    )


@router.patch("/{user_id}")
async def update_user(user_id: UUID, data: UpdateUserRequest, db: DbSession, current: CurrentUserDep) -> UserListItem:
    """Super admin or franchise admin updates a user."""
    current.require_permission("users.write")

    q = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    if "super_admin" not in current.roles:
        q = q.where(User.organization_id == current.org_id)

    user = (await db.execute(q)).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if data.full_name:
        user.full_name = data.full_name
    if data.password:
        user.password_hash = hash_password(data.password)
    if data.status:
        user.status = data.status

    if data.role:
        role_code = data.role if data.role in ALLOWED_ROLES else None
        if role_code:
            # Remove existing roles
            existing_roles = (await db.execute(
                select(UserRole).where(UserRole.user_id == user.id)
            )).scalars().all()
            for ur in existing_roles:
                await db.delete(ur)
            await db.flush()
            role_obj = (await db.execute(select(Role).where(Role.code == role_code))).scalar_one_or_none()
            if role_obj:
                db.add(UserRole(user_id=user.id, role_id=role_obj.id,
                                organization_id=user.organization_id, center_id=None))

    await db.commit()
    await db.refresh(user)

    roles_res = await db.execute(
        select(Role).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user.id)
    )
    user_roles = [r.code for r in roles_res.scalars().all()]

    org_name = None
    if user.organization_id:
        org_res = await db.execute(select(Organization).where(Organization.id == user.organization_id))
        org = org_res.scalar_one_or_none()
        org_name = org.name if org else None

    return UserListItem(
        id=user.id, email=user.email, full_name=user.full_name,
        status=user.status, organization_id=user.organization_id,
        organization_name=org_name, roles=user_roles,
    )


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: UUID, db: DbSession, current: CurrentUserDep) -> None:
    """Soft-delete a user."""
    current.require_permission("users.write")
    from datetime import datetime, timezone

    q = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    if "super_admin" not in current.roles:
        q = q.where(User.organization_id == current.org_id)

    user = (await db.execute(q)).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Prevent deleting yourself
    if user.id == current.user.id:
        raise HTTPException(400, "Cannot delete your own account")

    user.deleted_at = datetime.now(timezone.utc)
    await db.commit()
