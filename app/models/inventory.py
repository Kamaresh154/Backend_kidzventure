"""Inventory — products, stock levels, purchase orders."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonType, UuidType


class InventoryProduct(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "inventory_products"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="pcs", nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock_entries: Mapped[list["StockEntry"]] = relationship(back_populates="product")


class StockEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Each row is a stock movement (positive = in, negative = out)."""

    __tablename__ = "stock_entries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("centers.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("inventory_products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # positive=in, negative=out
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)  # purchase | sale | adjustment | transfer
    reference_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    product: Mapped["InventoryProduct"] = relationship(back_populates="stock_entries")
