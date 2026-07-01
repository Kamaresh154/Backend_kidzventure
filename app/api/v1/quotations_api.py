from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, ResolvedOrgDep
from app.schemas.quotation import (
    QuotationCreate, QuotationListResponse, QuotationResponse, QuotationStatusUpdate,
)
from app.services import quotation_service

router = APIRouter(prefix="/quotations", tags=["quotations"])


@router.get("", response_model=QuotationListResponse)
async def list_quotations(
    db: DbSession,
    current: CurrentUserDep,
    org_id: ResolvedOrgDep,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> QuotationListResponse:
    current.require_permission("invoices.read")
    items, total = await quotation_service.list_quotations(
        db, org_id, status=status, page=page, page_size=page_size
    )
    return QuotationListResponse(items=[QuotationResponse.model_validate(i) for i in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=QuotationResponse, status_code=201)
async def create_quotation(data: QuotationCreate, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> QuotationResponse:
    current.require_permission("invoices.write")
    quotation = await quotation_service.create_quotation(db, org_id, data)
    return QuotationResponse.model_validate(quotation)


@router.patch("/{quotation_id}/status", response_model=QuotationResponse)
async def update_quotation_status(
    quotation_id: UUID, data: QuotationStatusUpdate, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep
) -> QuotationResponse:
    current.require_permission("invoices.write")
    quotation = await quotation_service.update_quotation_status(db, org_id, quotation_id, data)
    return QuotationResponse.model_validate(quotation)


@router.delete("/{quotation_id}", status_code=204)
async def delete_quotation(quotation_id: UUID, db: DbSession, current: CurrentUserDep, org_id: ResolvedOrgDep) -> None:
    current.require_permission("invoices.write")
    await quotation_service.delete_quotation(db, org_id, quotation_id)
