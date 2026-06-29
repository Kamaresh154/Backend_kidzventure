from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LeadCreate(BaseModel):
    child_name: str = Field(min_length=1, max_length=255)
    child_age: int | None = Field(default=None, ge=0, le=18)
    parent_name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    center_id: UUID | None = None
    follow_up_date: date | None = None
    notes: str | None = None
    assigned_to: UUID | None = None


class LeadUpdate(BaseModel):
    child_name: str | None = None
    parent_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    status: str | None = None
    lost_reason: str | None = None
    follow_up_date: date | None = None
    notes: str | None = None
    assigned_to: UUID | None = None
    converted_student_id: UUID | None = None


class ActivityCreate(BaseModel):
    activity_type: str = Field(..., max_length=64)
    description: str = Field(min_length=1)


class ActivityResponse(ORMModel):
    id: UUID
    lead_id: UUID
    activity_type: str
    description: str
    created_by: UUID | None
    created_at: object


class LeadResponse(ORMModel):
    id: UUID
    organization_id: UUID
    center_id: UUID | None
    child_name: str
    child_age: int | None
    parent_name: str
    phone: str | None
    email: str | None
    source: str | None
    status: str
    lost_reason: str | None
    assigned_to: UUID | None
    follow_up_date: date | None
    notes: str | None
    converted_student_id: UUID | None
    created_at: object
    updated_at: object
    activities: list[ActivityResponse] = []


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
