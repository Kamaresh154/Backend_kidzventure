from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession
from app.schemas.inventory import (
    ProductCreate, ProductListResponse, ProductResponse, ProductUpdate,
    StockEntryCreate, StockEntryResponse,
)
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    db: DbSession,
    current: CurrentUserDep,
    category: str | None = None,
    low_stock_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=500),
) -> ProductListResponse:
    current.require_permission("inventory.read")
    items, total = await inventory_service.list_products(
        db, current.org_id, category=category, low_stock_only=low_stock_only,
        page=page, page_size=page_size,
    )
    return ProductListResponse(items=[ProductResponse.model_validate(i) for i in items], total=total, page=page, page_size=page_size)


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, db: DbSession, current: CurrentUserDep) -> ProductResponse:
    current.require_permission("inventory.write")
    product = await inventory_service.create_product(db, current.org_id, data)
    return ProductResponse.model_validate({**product.__dict__, "current_stock": 0})


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: UUID, data: ProductUpdate, db: DbSession, current: CurrentUserDep) -> ProductResponse:
    current.require_permission("inventory.write")
    product = await inventory_service.update_product(db, current.org_id, product_id, data)
    from app.services.inventory_service import _get_stock_level
    stock = await _get_stock_level(db, product.id)
    return ProductResponse.model_validate({**product.__dict__, "current_stock": stock})


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: UUID, db: DbSession, current: CurrentUserDep) -> None:
    current.require_permission("inventory.write")
    await inventory_service.delete_product(db, current.org_id, product_id)


@router.get("/products/{product_id}/stock", response_model=list[StockEntryResponse])
async def list_stock_entries(
    product_id: UUID,
    db: DbSession,
    current: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[StockEntryResponse]:
    current.require_permission("inventory.read")
    items, _ = await inventory_service.list_stock_entries(db, current.org_id, product_id, page=page, page_size=page_size)
    return [StockEntryResponse.model_validate(e) for e in items]


@router.post("/stock-entries", response_model=StockEntryResponse, status_code=201)
async def add_stock_entry(data: StockEntryCreate, db: DbSession, current: CurrentUserDep) -> StockEntryResponse:
    current.require_permission("inventory.write")
    entry = await inventory_service.add_stock_entry(db, current.org_id, data, current.user.id)
    return StockEntryResponse.model_validate(entry)
