from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class StaffProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    center_id: UUID | None = None
    user_id: UUID | None = None
    designation: str | None = None
    department: str | None = None
    employee_code: str | None = None
    date_of_joining: date | None = None
    basic_salary: Decimal = Field(default=Decimal("0"), ge=0)
    bank_account: dict = Field(default_factory=dict)
    status: str = "active"


class StaffProfileUpdate(BaseModel):
    full_name: str | None = None
    center_id: UUID | None = None
    designation: str | None = None
    department: str | None = None
    basic_salary: Decimal | None = None
    bank_account: dict | None = None
    status: str | None = None


class StaffProfileResponse(ORMModel):
    id: UUID
    organization_id: UUID
    center_id: UUID | None
    user_id: UUID | None
    full_name: str
    designation: str | None
    department: str | None
    employee_code: str | None
    date_of_joining: date | None
    basic_salary: Decimal
    status: str
    created_at: object
    updated_at: object


class StaffListResponse(BaseModel):
    items: list[StaffProfileResponse]
    total: int
    page: int
    page_size: int


class PayslipCreate(BaseModel):
    staff_id: UUID
    pay_period: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # YYYY-MM
    allowances: Decimal = Field(default=Decimal("0"), ge=0)
    deductions: Decimal = Field(default=Decimal("0"), ge=0)
    bonus: Decimal = Field(default=Decimal("0"), ge=0)
    breakdown: dict = Field(default_factory=dict)
    notes: str | None = None


class PayslipResponse(ORMModel):
    id: UUID
    organization_id: UUID
    staff_id: UUID
    pay_period: str
    basic_salary: Decimal
    allowances: Decimal
    deductions: Decimal
    bonus: Decimal
    gross_pay: Decimal
    net_pay: Decimal
    status: str
    breakdown: dict
    notes: str | None
    paid_at: date | None
    created_at: object
    updated_at: object


class PayslipListResponse(BaseModel):
    items: list[PayslipResponse]
    total: int
    page: int
    page_size: int
