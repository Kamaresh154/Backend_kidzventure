"""Finance ledger — double-entry accounting entries."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonType, UuidType

# Entry types (debit/credit from the perspective of the business):
#   REVENUE   – money earned (e.g. invoice paid)
#   EXPENSE   – money spent
#   PAYMENT   – cash/bank receipt that clears an invoice
#   REFUND    – reversal of a payment or revenue
#   ADJUSTMENT– manual correction


class LedgerAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Chart of accounts — one per organization, seeded on org creation."""

    __tablename__ = "ledger_accounts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # asset | liability | equity | revenue | expense
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(default=True, nullable=False)

    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="account")


class LedgerEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable ledger entry (single side of a double-entry transaction)."""

    __tablename__ = "ledger_entries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("centers.id", ondelete="SET NULL"), nullable=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("ledger_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    # Link to source document (optional)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    # debit or credit
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # debit | credit
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    entry_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # revenue | expense | payment | refund | adjustment
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # ISO date of the transaction (may differ from created_at)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meta: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    account: Mapped["LedgerAccount"] = relationship(back_populates="entries")
