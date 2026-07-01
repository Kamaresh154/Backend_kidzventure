from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LeaveRequestCreate(BaseModel):
    employee_id: UUID
    employee_name: str = Field(min_length=1, max_length=255)
    leave_type: str = Field(..., pattern="^(casual|sick|earned|unpaid|other)$")
    from_date: date
    to_date: date
    days: int = Field(ge=1)
    reason: str = Field(min_length=1)


class LeaveRequestReview(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    reviewed_by: str
    review_note: str | None = None


class LeaveRequestResponse(ORMModel):
    id: UUID
    organization_id: UUID
    employee_id: UUID
    employee_name: str
    leave_type: str
    from_date: date
    to_date: date
    days: int
    reason: str
    status: str
    reviewed_by: str | None
    reviewed_on: date | None
    review_note: str | None
    created_at: object
    updated_at: object


class LeaveListResponse(BaseModel):
    items: list[LeaveRequestResponse]
    total: int
    page: int
    page_size: int
