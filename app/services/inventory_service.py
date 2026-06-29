import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryProduct, StockEntry
from app.schemas.inventory import ProductCreate, ProductUpdate, StockEntryCreate


async def list_products(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    category: str | None = None,
    low_stock_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    q = select(InventoryProduct).where(
        InventoryProduct.organization_id == org_id,
        InventoryProduct.deleted_at.is_(None),
    )
    if category:
        q = q.where(InventoryProduct.category == category)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    products = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    result = []
    for p in products:
        stock = await _get_stock_level(db, p.id)
        item = {**p.__dict__, "current_stock": stock}
        if low_stock_only and stock > p.reorder_level:
            continue
        result.append(item)
    return result, total


async def _get_stock_level(db: AsyncSession, product_id: uuid.UUID) -> int:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(StockEntry.quantity), 0)).where(
                StockEntry.product_id == product_id
            )
        )
    ).scalar_one()
    return int(total)


async def create_product(db: AsyncSession, org_id: uuid.UUID, data: ProductCreate) -> InventoryProduct:
    product = InventoryProduct(organization_id=org_id, **data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession, org_id: uuid.UUID, product_id: uuid.UUID, data: ProductUpdate
) -> InventoryProduct:
    product = await _get_product(db, org_id, product_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(product, k, v)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, org_id: uuid.UUID, product_id: uuid.UUID) -> None:
    from datetime import datetime, timezone
    product = await _get_product(db, org_id, product_id)
    product.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def add_stock_entry(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: StockEntryCreate,
    created_by: uuid.UUID,
) -> StockEntry:
    # Validate product exists in org
    await _get_product(db, org_id, data.product_id)
    entry = StockEntry(
        organization_id=org_id,
        created_by=created_by,
        **data.model_dump(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_stock_entries(
    db: AsyncSession,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[StockEntry], int]:
    q = select(StockEntry).where(
        StockEntry.organization_id == org_id,
        StockEntry.product_id == product_id,
    )
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (
        await db.execute(q.order_by(StockEntry.entry_date.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return list(items), total


async def _get_product(db: AsyncSession, org_id: uuid.UUID, product_id: uuid.UUID) -> InventoryProduct:
    result = await db.execute(
        select(InventoryProduct).where(
            InventoryProduct.id == product_id,
            InventoryProduct.organization_id == org_id,
            InventoryProduct.deleted_at.is_(None),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p
