import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_otp,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth import OtpVerification, RefreshToken
from app.models.organization import Center, Organization
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse


async def _load_user_roles_permissions(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[list[str], list[str]]:
    result = await db.execute(
        select(UserRole, Role)
        .join(Role, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    rows = result.all()
    role_codes = [role.code for _, role in rows]

    if not role_codes:
        return [], []

    perm_result = await db.execute(
        select(Permission.code)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Role.code.in_(role_codes))
    )
    permissions = list({row[0] for row in perm_result.all()})
    return role_codes, permissions


async def issue_tokens(
    db: AsyncSession,
    user: User,
    *,
    device_id: str | None = None,
    device_name: str | None = None,
) -> TokenResponse:
    roles, permissions = await _load_user_roles_permissions(db, user.id)
    org_id = str(user.organization_id) if user.organization_id else None

    access = create_access_token(
        sub=str(user.id),
        org_id=org_id,
        roles=roles,
        permissions=permissions,
    )

    raw_refresh = generate_refresh_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            device_id=device_id,
            device_name=device_name,
            expires_at=expires,
        )
    )

    user.last_login_at = datetime.now(timezone.utc)

    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def register_organization_owner(db: AsyncSession, data: RegisterRequest) -> TokenResponse:
    slug = data.organization_slug.lower().strip()
    if not re.match(r"^[a-z0-9-]+$", slug):
        raise HTTPException(status_code=400, detail="Invalid organization slug")

    existing_org = await db.execute(
        select(Organization).where(Organization.slug == slug, Organization.deleted_at.is_(None))
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    existing_user = await db.execute(
        select(User).where(User.email == data.email.lower(), User.deleted_at.is_(None))
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    org = Organization(name=data.organization_name, slug=slug)
    db.add(org)
    await db.flush()

    center = Center(
        organization_id=org.id,
        name=f"{org.name} — Main",
        code="MAIN",
    )
    db.add(center)

    user = User(
        organization_id=org.id,
        email=data.email.lower(),
        phone=data.phone,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        status="active",
    )
    db.add(user)
    await db.flush()

    role_result = await db.execute(select(Role).where(Role.code == "franchise_owner"))
    owner_role = role_result.scalar_one()
    db.add(
        UserRole(
            user_id=user.id,
            role_id=owner_role.id,
            organization_id=org.id,
            center_id=None,
        )
    )

    return await issue_tokens(db, user)


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
    *,
    device_id: str | None = None,
    device_name: str | None = None,
) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    return await issue_tokens(db, user, device_id=device_id, device_name=device_name)


async def refresh_access_token(db: AsyncSession, raw_refresh: str) -> TokenResponse:
    token_hash = hash_token(raw_refresh)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )
    stored = result.scalar_one_or_none()
    if stored is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_result = await db.execute(
        select(User).where(User.id == stored.user_id, User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    stored.revoked_at = now
    return await issue_tokens(db, user)


async def create_password_reset_otp(db: AsyncSession, email: str) -> None:
    result = await db.execute(
        select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        return

    code = generate_otp_code()
    db.add(
        OtpVerification(
            user_id=user.id,
            channel="email",
            destination=email.lower(),
            code_hash=hash_otp(code),
            purpose="reset_password",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
    )
    # TODO: send email via provider; dev logs OTP in debug mode
    if settings.debug:
        print(f"[DEV] Password reset OTP for {email}: {code}")


async def reset_password_with_otp(
    db: AsyncSession, email: str, otp: str, new_password: str
) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(OtpVerification)
        .where(
            OtpVerification.destination == email.lower(),
            OtpVerification.purpose == "reset_password",
            OtpVerification.consumed_at.is_(None),
            OtpVerification.expires_at > now,
        )
        .order_by(OtpVerification.created_at.desc())
    )
    record = result.scalar_one_or_none()
    if record is None or record.code_hash != hash_otp(otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user_result = await db.execute(
        select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(new_password)
    record.consumed_at = now
