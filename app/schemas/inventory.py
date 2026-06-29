from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str | None = None
    category: str | None = None
    unit: str = "pcs"
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_level: int = Field(default=0, ge=0)
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    sku: str | None = None
    category: str | None = None
    unit: str | None = None
    unit_cost: Decimal | None = None
    reorder_level: int | None = None
    description: str | None = None


class ProductResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    sku: str | None
    category: str | None
    unit: str
    unit_cost: Decimal
    reorder_level: int
    description: str | None
    current_stock: int = 0
    created_at: object
    updated_at: object


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


class StockEntryCreate(BaseModel):
    product_id: UUID
    center_id: UUID | None = None
    quantity: int = Field(..., ne=0)
    entry_type: str = Field(..., pattern="^(purchase|sale|adjustment|transfer)$")
    reference_no: str | None = None
    unit_cost: Decimal | None = None
    notes: str | None = None
    entry_date: date


class StockEntryResponse(ORMModel):
    id: UUID
    organization_id: UUID
    center_id: UUID | None
    product_id: UUID
    quantity: int
    entry_type: str
    reference_no: str | None
    unit_cost: Decimal | None
    notes: str | None
    entry_date: date
    created_at: object
