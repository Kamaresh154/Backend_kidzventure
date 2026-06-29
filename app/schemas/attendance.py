from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AttendanceCheckIn(BaseModel):
    student_id: UUID | None = None
    qr_code: str | None = None
    center_id: UUID
    method: str = "manual"
    notes: str | None = None


class AttendanceCheckOut(BaseModel):
    notes: str | None = None


class AttendanceResponse(ORMModel):
    id: UUID
    organization_id: UUID
    center_id: UUID
    student_id: UUID
    student_name: str | None = None
    check_in_at: datetime
    check_out_at: datetime | None
    method: str
    notes: str | None
    created_at: datetime


class AttendanceListResponse(BaseModel):
    items: list[AttendanceResponse]
    total: int
    page: int
    page_size: int


class AttendanceSummary(BaseModel):
    date: date
    present: int
    checked_out: int
    still_in: int
