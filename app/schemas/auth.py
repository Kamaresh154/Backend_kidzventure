from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)
    organization_slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    phone: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str
    device_id: str | None = None
    device_name: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8)
    purpose: str = "signup"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    organization_id: str | None
    roles: list[str]
    permissions: list[str]

    model_config = {"from_attributes": True}