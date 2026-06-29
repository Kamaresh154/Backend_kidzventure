from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# ── Accounts ────────────────────────────────────────────────────────────────

class LedgerAccountResponse(ORMModel):
    id: UUID
    organization_id: UUID
    code: str
    name: str
    account_type: str
    currency: str
    description: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


# ── Entries ──────────────────────────────────────────────────────────────────

class LedgerEntryCreate(BaseModel):
    account_id: UUID
    center_id: UUID | None = None
    invoice_id: UUID | None = None
    direction: str = Field(..., pattern="^(debit|credit)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="INR", max_length=8)
    entry_type: str = Field(
        ..., pattern="^(revenue|expense|payment|refund|adjustment)$"
    )
    description: str = Field(min_length=1, max_length=500)
    reference_no: str | None = Field(default=None, max_length=128)
    entry_date: datetime
    meta: dict = Field(default_factory=dict)


class LedgerEntryResponse(ORMModel):
    id: UUID
    organization_id: UUID
    center_id: UUID | None
    account_id: UUID
    invoice_id: UUID | None
    direction: str
    amount: Decimal
    currency: str
    entry_type: str
    description: str
    reference_no: str | None
    entry_date: datetime
    meta: dict
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class LedgerEntryListResponse(BaseModel):
    items: list[LedgerEntryResponse]
    total: int
    page: int
    page_size: int


# ── Balance Summary ──────────────────────────────────────────────────────────

class AccountBalance(BaseModel):
    account_id: UUID
    code: str
    name: str
    account_type: str
    currency: str
    total_debit: Decimal
    total_credit: Decimal
    balance: Decimal  # net (debit - credit) for asset/expense; (credit - debit) for liability/revenue/equity


class LedgerSummaryResponse(BaseModel):
    organization_id: UUID
    from_date: datetime | None
    to_date: datetime | None
    accounts: list[AccountBalance]
    total_revenue: Decimal
    total_expense: Decimal
    net_income: Decimal
