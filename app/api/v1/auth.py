from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep, DbSession
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserProfile,
)
from app.schemas.common import MessageResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: DbSession) -> TokenResponse:
    return await auth_service.register_organization_owner(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DbSession) -> TokenResponse:
    return await auth_service.login_user(
        db,
        data.email,
        data.password,
        device_id=data.device_id,
        device_name=data.device_name,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: DbSession) -> TokenResponse:
    return await auth_service.refresh_access_token(db, data.refresh_token)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest, db: DbSession) -> MessageResponse:
    await auth_service.create_password_reset_otp(db, data.email)
    return MessageResponse(message="If the email exists, a reset code has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest, db: DbSession) -> MessageResponse:
    await auth_service.reset_password_with_otp(
        db, data.email, data.otp, data.new_password
    )
    return MessageResponse(message="Password updated successfully.")


@router.get("/me", response_model=UserProfile)
async def me(current: CurrentUserDep) -> UserProfile:
    return UserProfile(
        id=str(current.user.id),
        email=current.user.email,
        full_name=current.user.full_name,
        organization_id=str(current.user.organization_id) if current.user.organization_id else None,
        roles=current.roles,
        permissions=current.permissions,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(_request: Request, current: CurrentUserDep) -> MessageResponse:
    # Client should discard tokens; optional server-side revoke all refresh tokens in Phase 2
    _ = current
    return MessageResponse(message="Logged out.")