import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceLine
from app.models.organization import Center
from app.models.student import Parent, Student
from app.schemas.invoice import InvoiceCreate, InvoiceLineCreate, InvoiceUpdate


def _line_amount(line: InvoiceLineCreate) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = line.qty * line.unit_price
    tax = (subtotal * line.tax_rate / Decimal("100")).quantize(Decimal("0.01"))
    return subtotal, tax, subtotal + tax


def _totals(lines: list[InvoiceLineCreate]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = Decimal("0")
    tax = Decimal("0")
    for line in lines:
        s, t, _ = _line_amount(line)
        subtotal += s
        tax += t
    total = subtotal + tax
    return subtotal.quantize(Decimal("0.01")), tax.quantize(Decimal("0.01")), total.quantize(Decimal("0.01"))


async def _next_invoice_no(db: AsyncSession, org_id: uuid.UUID) -> str:
    count = (
        await db.execute(
            select(func.count()).select_from(Invoice).where(Invoice.organization_id == org_id)
        )
    ).scalar_one()
    return f"INV-{count + 1:05d}"


async def list_invoices(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: str | None = None,
    center_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Invoice], int]:
    query = (
        select(Invoice)
        .where(Invoice.organization_id == org_id, Invoice.deleted_at.is_(None))
        .options(selectinload(Invoice.lines))
    )
    if status:
        query = query.where(Invoice.status == status)
    if center_id:
        query = query.where(Invoice.center_id == center_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(
        query.order_by(Invoice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all()), total


async def get_invoice(db: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.organization_id == org_id,
            Invoice.deleted_at.is_(None),
        )
        .options(selectinload(Invoice.lines))
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


async def create_invoice(db: AsyncSession, org_id: uuid.UUID, data: InvoiceCreate) -> Invoice:
    center_ok = await db.execute(
        select(Center).where(
            Center.id == data.center_id,
            Center.organization_id == org_id,
            Center.deleted_at.is_(None),
        )
    )
    if center_ok.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Invalid center")

    if data.student_id:
        s = await db.execute(
            select(Student).where(
                Student.id == data.student_id,
                Student.organization_id == org_id,
                Student.deleted_at.is_(None),
            )
        )
        if s.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="Invalid student")

    if data.parent_id:
        p = await db.execute(
            select(Parent).where(
                Parent.id == data.parent_id,
                Parent.organization_id == org_id,
                Parent.deleted_at.is_(None),
            )
        )
        if p.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="Invalid parent")

    subtotal, tax_amount, total = _totals(data.lines)
    invoice = Invoice(
        organization_id=org_id,
        center_id=data.center_id,
        invoice_no=await _next_invoice_no(db, org_id),
        student_id=data.student_id,
        parent_id=data.parent_id,
        status="draft",
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        due_date=data.due_date,
        notes=data.notes,
    )
    db.add(invoice)
    await db.flush()

    for line_data in data.lines:
        s, t, amount = _line_amount(line_data)
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description=line_data.description,
                qty=line_data.qty,
                unit_price=line_data.unit_price,
                tax_rate=line_data.tax_rate,
                amount=amount,
            )
        )
    await db.flush()
    return invoice


async def update_invoice(
    db: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID, data: InvoiceUpdate
) -> Invoice:
    invoice = await get_invoice(db, org_id, invoice_id)
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be edited")

    if data.due_date is not None:
        invoice.due_date = data.due_date
    if data.notes is not None:
        invoice.notes = data.notes
    if data.student_id is not None:
        invoice.student_id = data.student_id
    if data.parent_id is not None:
        invoice.parent_id = data.parent_id
    return invoice


async def send_invoice(db: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    invoice = await get_invoice(db, org_id, invoice_id)
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Invoice is not a draft")
    invoice.status = "sent"
    invoice.issued_at = datetime.now(timezone.utc)
    return invoice


async def mark_paid(db: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    invoice = await get_invoice(db, org_id, invoice_id)
    if invoice.status not in ("sent", "overdue"):
        raise HTTPException(status_code=400, detail="Invoice cannot be marked paid")
    invoice.status = "paid"
    invoice.paid_at = datetime.now(timezone.utc)
    return invoice


async def cancel_invoice(db: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    invoice = await get_invoice(db, org_id, invoice_id)
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Paid invoices cannot be cancelled")
    invoice.status = "cancelled"
    return invoice


async def soft_delete_invoice(db: AsyncSession, org_id: uuid.UUID, invoice_id: uuid.UUID) -> None:
    invoice = await get_invoice(db, org_id, invoice_id)
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Cannot delete paid invoice")
    invoice.deleted_at = datetime.now(timezone.utc)
