from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str = "free"


class OrganizationUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    settings: dict | None = None


class OrganizationResponse(ORMModel):
    id: UUID
    name: str
    slug: str
    plan: str
    settings: dict
    created_at: datetime
    updated_at: datetime


class CenterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    address: dict = Field(default_factory=dict)
    timezone: str = "Asia/Kolkata"


class CenterUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: dict | None = None
    timezone: str | None = None


class CenterResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str | None
    address: dict
    timezone: str
    created_at: datetime
    updated_at: datetime
