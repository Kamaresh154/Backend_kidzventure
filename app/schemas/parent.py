from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class ParentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    email: EmailStr | None = None


class ParentUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class ParentResponse(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID | None
    full_name: str
    phone: str | None
    email: str | None
    created_at: datetime
    updated_at: datetime


class ParentLinkRequest(BaseModel):
    student_id: UUID
    relationship: str | None = None
    is_primary: bool = False


class LinkedStudentBrief(BaseModel):
    id: UUID
    full_name: str
    admission_no: str | None
    relationship: str | None
    is_primary: bool


class ParentDetailResponse(ParentResponse):
    students: list[LinkedStudentBrief] = []


class ParentListResponse(BaseModel):
    items: list[ParentResponse]
    total: int
    page: int
    page_size: int
