"""Finance ledger service — querying and creating ledger entries."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.ledger import LedgerAccount, LedgerEntry
from app.models.organization import Center
from app.schemas.ledger import (
    AccountBalance,
    LedgerAccountCreate,
    LedgerEntryCreate,
    LedgerSummaryResponse,
)

# ── Default chart of accounts seeded for every new org ──────────────────────

DEFAULT_ACCOUNTS = [
    # code, name, type
    ("1000", "Cash & Bank", "asset"),
    ("1100", "Accounts Receivable", "asset"),
    ("2000", "Accounts Payable", "liability"),
    ("3000", "Owner's Equity", "equity"),
    ("4000", "Tuition Revenue", "revenue"),
    ("4100", "Fee Revenue", "revenue"),
    ("4900", "Other Revenue", "revenue"),
    ("5000", "Salary Expense", "expense"),
    ("5100", "Rent & Utilities", "expense"),
    ("5900", "Other Expense", "expense"),
]


async def ensure_chart_of_accounts(db: AsyncSession, org_id: uuid.UUID) -> None:
    """Idempotently seed the default accounts for an org."""
    existing = (
        await db.execute(
            select(func.count()).select_from(LedgerAccount).where(
                LedgerAccount.organization_id == org_id
            )
        )
    ).scalar_one()
    if existing:
        return

    for code, name, acct_type in DEFAULT_ACCOUNTS:
        db.add(
            LedgerAccount(
                organization_id=org_id,
                code=code,
                name=name,
                account_type=acct_type,
                is_system=True,
            )
        )
    await db.flush()


async def create_account(
    db: AsyncSession, org_id: uuid.UUID, data: LedgerAccountCreate
) -> LedgerAccount:
    account = LedgerAccount(
        organization_id=org_id,
        code=data.code,
        name=data.name,
        account_type=data.account_type,
        description=data.description,
        is_system=False,
    )
    db.add(account)
    await db.flush()
    return account


async def list_accounts(db: AsyncSession, org_id: uuid.UUID) -> list[LedgerAccount]:
    result = await db.execute(
        select(LedgerAccount)
        .where(LedgerAccount.organization_id == org_id)
        .order_by(LedgerAccount.code)
    )
    return list(result.scalars().all())


async def get_account(
    db: AsyncSession, org_id: uuid.UUID, account_id: uuid.UUID
) -> LedgerAccount:
    result = await db.execute(
        select(LedgerAccount).where(
            LedgerAccount.id == account_id,
            LedgerAccount.organization_id == org_id,
        )
    )
    acct = result.scalar_one_or_none()
    if acct is None:
        raise HTTPException(status_code=404, detail="Ledger account not found")
    return acct


async def list_entries(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    account_id: uuid.UUID | None = None,
    invoice_id: uuid.UUID | None = None,
    entry_type: str | None = None,
    center_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[LedgerEntry], int]:
    q = select(LedgerEntry).where(LedgerEntry.organization_id == org_id)
    if account_id:
        q = q.where(LedgerEntry.account_id == account_id)
    if invoice_id:
        q = q.where(LedgerEntry.invoice_id == invoice_id)
    if entry_type:
        q = q.where(LedgerEntry.entry_type == entry_type)
    if center_id:
        q = q.where(LedgerEntry.center_id == center_id)
    if from_date:
        q = q.where(LedgerEntry.entry_date >= from_date)
    if to_date:
        q = q.where(LedgerEntry.entry_date <= to_date)

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    items = (
        await db.execute(
            q.order_by(LedgerEntry.entry_date.desc(), LedgerEntry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return list(items), total


async def create_entry(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: LedgerEntryCreate,
    created_by: uuid.UUID | None = None,
) -> LedgerEntry:
    # Validate account belongs to org
    await get_account(db, org_id, data.account_id)

    # Validate center if provided
    if data.center_id:
        c = await db.execute(
            select(Center).where(
                Center.id == data.center_id, Center.organization_id == org_id
            )
        )
        if c.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="Invalid center")

    # Validate invoice if provided
    if data.invoice_id:
        inv = await db.execute(
            select(Invoice).where(
                Invoice.id == data.invoice_id,
                Invoice.organization_id == org_id,
                Invoice.deleted_at.is_(None),
            )
        )
        if inv.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="Invalid invoice")

    entry = LedgerEntry(
        organization_id=org_id,
        center_id=data.center_id,
        account_id=data.account_id,
        invoice_id=data.invoice_id,
        direction=data.direction,
        amount=data.amount.quantize(Decimal("0.01")),
        currency=data.currency,
        entry_type=data.entry_type,
        description=data.description,
        reference_no=data.reference_no,
        entry_date=data.entry_date,
        meta=data.meta,
        created_by=created_by,
    )
    db.add(entry)
    await db.flush()
    return entry


async def record_invoice_paid(
    db: AsyncSession,
    org_id: uuid.UUID,
    invoice: Invoice,
    created_by: uuid.UUID | None = None,
) -> list[LedgerEntry]:
    """Auto-post two ledger entries when an invoice is marked paid:
      Debit  Cash & Bank (asset +)
      Credit Tuition Revenue (revenue +)
    """
    await ensure_chart_of_accounts(db, org_id)

    accounts = {a.code: a for a in await list_accounts(db, org_id)}
    cash_acct = accounts.get("1000")
    rev_acct = accounts.get("4000")
    if not cash_acct or not rev_acct:
        return []

    now = datetime.now(timezone.utc)
    entries = []
    for direction, account in [("debit", cash_acct), ("credit", rev_acct)]:
        e = LedgerEntry(
            organization_id=org_id,
            center_id=invoice.center_id,
            account_id=account.id,
            invoice_id=invoice.id,
            direction=direction,
            amount=invoice.total,
            currency="INR",
            entry_type="payment" if direction == "debit" else "revenue",
            description=f"Invoice {invoice.invoice_no} — {'receipt' if direction == 'debit' else 'revenue'}",
            reference_no=invoice.invoice_no,
            entry_date=now,
            meta={},
            created_by=created_by,
        )
        db.add(e)
        entries.append(e)
    await db.flush()
    return entries


async def get_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> LedgerSummaryResponse:
    await ensure_chart_of_accounts(db, org_id)
    accounts = await list_accounts(db, org_id)

    balances: list[AccountBalance] = []
    total_revenue = Decimal("0")
    total_expense = Decimal("0")

    for acct in accounts:
        q = select(LedgerEntry).where(
            LedgerEntry.organization_id == org_id,
            LedgerEntry.account_id == acct.id,
        )
        if from_date:
            q = q.where(LedgerEntry.entry_date >= from_date)
        if to_date:
            q = q.where(LedgerEntry.entry_date <= to_date)

        rows = (await db.execute(q)).scalars().all()

        total_debit = sum((e.amount for e in rows if e.direction == "debit"), Decimal("0"))
        total_credit = sum((e.amount for e in rows if e.direction == "credit"), Decimal("0"))

        # Normal balance convention
        if acct.account_type in ("asset", "expense"):
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        balances.append(
            AccountBalance(
                account_id=acct.id,
                code=acct.code,
                name=acct.name,
                account_type=acct.account_type,
                currency=acct.currency,
                total_debit=total_debit,
                total_credit=total_credit,
                balance=balance,
            )
        )

        if acct.account_type == "revenue":
            total_revenue += balance
        elif acct.account_type == "expense":
            total_expense += balance

    return LedgerSummaryResponse(
        organization_id=org_id,
        from_date=from_date,
        to_date=to_date,
        accounts=balances,
        total_revenue=total_revenue,
        total_expense=total_expense,
        net_income=total_revenue - total_expense,
    )
