from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class InvoiceLineCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    qty: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class InvoiceLineResponse(ORMModel):
    id: UUID
    description: str
    qty: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    amount: Decimal


class InvoiceCreate(BaseModel):
    center_id: UUID
    student_id: UUID | None = None
    parent_id: UUID | None = None
    due_date: date | None = None
    notes: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


class InvoiceUpdate(BaseModel):
    due_date: date | None = None
    notes: str | None = None
    student_id: UUID | None = None
    parent_id: UUID | None = None


class InvoiceResponse(ORMModel):
    id: UUID
    organization_id: UUID
    center_id: UUID
    invoice_no: str
    student_id: UUID | None
    parent_id: UUID | None
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    due_date: date | None
    notes: str | None
    issued_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineResponse] = []


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
