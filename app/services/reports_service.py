"""Reports & analytics — P&L, balance sheet, attendance trends, enrolment stats."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceRecord
from app.models.crm import Lead
from app.models.invoice import Invoice
from app.models.ledger import LedgerAccount, LedgerEntry
from app.models.student import Student


async def get_pl_report(
    db: AsyncSession,
    org_id: uuid.UUID,
    from_date: datetime,
    to_date: datetime,
) -> dict:
    """Profit & Loss: Revenue accounts vs Expense accounts."""
    rows = (
        await db.execute(
            select(
                LedgerAccount.code,
                LedgerAccount.name,
                LedgerAccount.account_type,
                func.sum(
                    func.case(
                        (LedgerEntry.direction == "credit", LedgerEntry.amount),
                        else_=0,
                    )
                ).label("total_credit"),
                func.sum(
                    func.case(
                        (LedgerEntry.direction == "debit", LedgerEntry.amount),
                        else_=0,
                    )
                ).label("total_debit"),
            )
            .join(LedgerEntry, LedgerEntry.account_id == LedgerAccount.id)
            .where(
                LedgerAccount.organization_id == org_id,
                LedgerEntry.entry_date >= from_date,
                LedgerEntry.entry_date <= to_date,
                LedgerAccount.account_type.in_(["revenue", "expense"]),
            )
            .group_by(LedgerAccount.id, LedgerAccount.code, LedgerAccount.name, LedgerAccount.account_type)
        )
    ).all()

    revenue_lines = []
    expense_lines = []
    total_revenue = 0
    total_expense = 0

    for row in rows:
        if row.account_type == "revenue":
            amt = float(row.total_credit) - float(row.total_debit)
            revenue_lines.append({"code": row.code, "name": row.name, "amount": amt})
            total_revenue += amt
        else:
            amt = float(row.total_debit) - float(row.total_credit)
            expense_lines.append({"code": row.code, "name": row.name, "amount": amt})
            total_expense += amt

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "revenue": revenue_lines,
        "expenses": expense_lines,
        "total_revenue": round(total_revenue, 2),
        "total_expense": round(total_expense, 2),
        "net_profit": round(total_revenue - total_expense, 2),
    }


async def get_balance_sheet(db: AsyncSession, org_id: uuid.UUID, as_of: datetime) -> dict:
    """Balance sheet — assets, liabilities, equity."""
    rows = (
        await db.execute(
            select(
                LedgerAccount.code,
                LedgerAccount.name,
                LedgerAccount.account_type,
                func.sum(
                    func.case(
                        (LedgerEntry.direction == "debit", LedgerEntry.amount),
                        else_=-LedgerEntry.amount,
                    )
                ).label("balance"),
            )
            .join(LedgerEntry, LedgerEntry.account_id == LedgerAccount.id)
            .where(
                LedgerAccount.organization_id == org_id,
                LedgerEntry.entry_date <= as_of,
                LedgerAccount.account_type.in_(["asset", "liability", "equity"]),
            )
            .group_by(LedgerAccount.id, LedgerAccount.code, LedgerAccount.name, LedgerAccount.account_type)
        )
    ).all()

    assets, liabilities, equity = [], [], []
    totals = {"asset": 0.0, "liability": 0.0, "equity": 0.0}
    for row in rows:
        b = float(row.balance)
        entry = {"code": row.code, "name": row.name, "balance": b}
        totals[row.account_type] += b
        {"asset": assets, "liability": liabilities, "equity": equity}[row.account_type].append(entry)

    return {
        "as_of": as_of.isoformat(),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": round(totals["asset"], 2),
        "total_liabilities": round(totals["liability"], 2),
        "total_equity": round(totals["equity"], 2),
    }


async def get_gst_report(
    db: AsyncSession,
    org_id: uuid.UUID,
    from_date: datetime,
    to_date: datetime,
) -> dict:
    """GST collected from invoices in the period."""
    rows = (
        await db.execute(
            select(
                func.sum(Invoice.tax_amount).label("total_gst"),
                func.sum(Invoice.subtotal).label("total_taxable"),
                func.sum(Invoice.total).label("total_invoiced"),
                func.count().label("invoice_count"),
            )
            .where(
                Invoice.organization_id == org_id,
                Invoice.status.in_(["paid", "sent"]),
                Invoice.issued_at >= from_date,
                Invoice.issued_at <= to_date,
            )
        )
    ).one()

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "invoice_count": rows.invoice_count or 0,
        "total_taxable": float(rows.total_taxable or 0),
        "total_gst_collected": float(rows.total_gst or 0),
        "total_invoiced": float(rows.total_invoiced or 0),
    }


async def get_attendance_trend(
    db: AsyncSession,
    org_id: uuid.UUID,
    from_date: datetime,
    to_date: datetime,
    center_id: uuid.UUID | None = None,
) -> list[dict]:
    """Daily attendance present counts."""
    q = (
        select(
            func.date(AttendanceRecord.check_in_at).label("day"),
            func.count().label("present"),
        )
        .where(
            AttendanceRecord.organization_id == org_id,
            AttendanceRecord.check_in_at >= from_date,
            AttendanceRecord.check_in_at <= to_date,
        )
        .group_by(func.date(AttendanceRecord.check_in_at))
        .order_by(func.date(AttendanceRecord.check_in_at))
    )
    if center_id:
        q = q.where(AttendanceRecord.center_id == center_id)
    rows = (await db.execute(q)).all()
    return [{"date": str(r.day), "present": r.present} for r in rows]


async def get_enrolment_trend(
    db: AsyncSession,
    org_id: uuid.UUID,
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """Monthly new student enrolments."""
    rows = (
        await db.execute(
            select(
                func.date_trunc("month", Student.created_at).label("month"),
                func.count().label("count"),
            )
            .where(
                Student.organization_id == org_id,
                Student.created_at >= from_date,
                Student.created_at <= to_date,
                Student.deleted_at.is_(None),
            )
            .group_by(func.date_trunc("month", Student.created_at))
            .order_by(func.date_trunc("month", Student.created_at))
        )
    ).all()
    return [{"month": str(r.month)[:7], "count": r.count} for r in rows]


async def get_revenue_trend(
    db: AsyncSession,
    org_id: uuid.UUID,
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """Monthly revenue from ledger."""
    rows = (
        await db.execute(
            select(
                func.date_trunc("month", LedgerEntry.entry_date).label("month"),
                func.sum(LedgerEntry.amount).label("revenue"),
            )
            .join(LedgerAccount, LedgerEntry.account_id == LedgerAccount.id)
            .where(
                LedgerEntry.organization_id == org_id,
                LedgerEntry.entry_date >= from_date,
                LedgerEntry.entry_date <= to_date,
                LedgerEntry.direction == "credit",
                LedgerAccount.account_type == "revenue",
            )
            .group_by(func.date_trunc("month", LedgerEntry.entry_date))
            .order_by(func.date_trunc("month", LedgerEntry.entry_date))
        )
    ).all()
    return [{"month": str(r.month)[:7], "revenue": float(r.revenue)} for r in rows]
