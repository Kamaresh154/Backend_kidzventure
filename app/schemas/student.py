from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class StudentCreate(BaseModel):
    center_id: UUID
    full_name: str = Field(min_length=1, max_length=255)
    admission_no: str | None = None
    dob: date | None = None
    gender: str | None = None
    batch_id: UUID | None = None
    medical_notes: str | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = None
    admission_no: str | None = None
    dob: date | None = None
    gender: str | None = None
    batch_id: UUID | None = None
    medical_notes: str | None = None
    status: str | None = None
    center_id: UUID | None = None


class StudentResponse(ORMModel):
    id: UUID
    organization_id: UUID
    center_id: UUID
    batch_id: UUID | None
    admission_no: str | None
    full_name: str
    dob: date | None
    gender: str | None
    qr_code: str | None
    medical_notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class StudentListResponse(BaseModel):
    items: list[StudentResponse]
    total: int
    page: int
    page_size: int
