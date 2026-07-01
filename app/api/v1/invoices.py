from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, ResolvedOrgDep
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.services import invoice_service, ledger_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _to_response(inv) -> InvoiceResponse:
    return InvoiceResponse.model_validate(inv)


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    current: CurrentUserDep,
    db: DbSession,
    org_id: ResolvedOrgDep,
    status: str | None = None,
    center_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> InvoiceListResponse:
    current.require_permission("invoices.read")
    items, total = await invoice_service.list_invoices(
        db, org_id, status=status, center_id=center_id, page=page, page_size=page_size
    )
    return InvoiceListResponse(
        items=[_to_response(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    data: InvoiceCreate, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> InvoiceResponse:
    current.require_permission("invoices.write")
    inv = await invoice_service.create_invoice(db, org_id, data)
    inv = await invoice_service.get_invoice(db, org_id, inv.id)
    return _to_response(inv)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> InvoiceResponse:
    current.require_permission("invoices.read")
    return _to_response(await invoice_service.get_invoice(db, org_id, invoice_id))


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    current: CurrentUserDep,
    db: DbSession,
    org_id: ResolvedOrgDep,
) -> InvoiceResponse:
    current.require_permission("invoices.write")
    await invoice_service.update_invoice(db, org_id, invoice_id, data)
    return _to_response(await invoice_service.get_invoice(db, org_id, invoice_id))


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: UUID, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> InvoiceResponse:
    current.require_permission("invoices.write")
    inv = await invoice_service.send_invoice(db, org_id, invoice_id)
    return _to_response(inv)


@router.post("/{invoice_id}/pay", response_model=InvoiceResponse)
async def mark_paid(
    invoice_id: UUID, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> InvoiceResponse:
    current.require_permission("invoices.write")
    inv = await invoice_service.mark_paid(db, org_id, invoice_id)
    # Auto-post double-entry ledger entries
    await ledger_service.record_invoice_paid(db, org_id, inv, created_by=current.user.id)
    return _to_response(inv)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: UUID, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> InvoiceResponse:
    current.require_permission("invoices.write")
    inv = await invoice_service.cancel_invoice(db, org_id, invoice_id)
    return _to_response(inv)


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: UUID, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> None:
    current.require_permission("invoices.write")
    await invoice_service.soft_delete_invoice(db, org_id, invoice_id)
