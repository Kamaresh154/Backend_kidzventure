from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, DbSession, ResolvedOrgDep
from app.schemas.ledger import (
    LedgerAccountResponse,
    LedgerEntryCreate,
    LedgerEntryListResponse,
    LedgerEntryResponse,
    LedgerSummaryResponse,
)
from app.services import ledger_service

router = APIRouter(prefix="/ledger", tags=["ledger"])


# ── Accounts ────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=list[LedgerAccountResponse])
async def list_accounts(current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep) -> list[LedgerAccountResponse]:
    current.require_permission("ledger.read")
    await ledger_service.ensure_chart_of_accounts(db, org_id)
    accounts = await ledger_service.list_accounts(db, org_id)
    return [LedgerAccountResponse.model_validate(a) for a in accounts]


@router.get("/accounts/{account_id}", response_model=LedgerAccountResponse)
async def get_account(
    account_id: UUID, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> LedgerAccountResponse:
    current.require_permission("ledger.read")
    acct = await ledger_service.get_account(db, org_id, account_id)
    return LedgerAccountResponse.model_validate(acct)


# ── Entries ──────────────────────────────────────────────────────────────────

@router.get("/entries", response_model=LedgerEntryListResponse)
async def list_entries(
    current: CurrentUserDep,
    db: DbSession,
    org_id: ResolvedOrgDep,
    account_id: UUID | None = None,
    invoice_id: UUID | None = None,
    entry_type: str | None = None,
    center_id: UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> LedgerEntryListResponse:
    current.require_permission("ledger.read")
    items, total = await ledger_service.list_entries(
        db,
        org_id,
        account_id=account_id,
        invoice_id=invoice_id,
        entry_type=entry_type,
        center_id=center_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return LedgerEntryListResponse(
        items=[LedgerEntryResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/entries", response_model=LedgerEntryResponse, status_code=201)
async def create_entry(
    data: LedgerEntryCreate, current: CurrentUserDep, db: DbSession, org_id: ResolvedOrgDep
) -> LedgerEntryResponse:
    current.require_permission("ledger.write")
    entry = await ledger_service.create_entry(
        db, org_id, data, created_by=current.user.id
    )
    return LedgerEntryResponse.model_validate(entry)


# ── Summary ──────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=LedgerSummaryResponse)
async def get_summary(
    current: CurrentUserDep,
    db: DbSession,
    org_id: ResolvedOrgDep,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> LedgerSummaryResponse:
    current.require_permission("ledger.read")
    return await ledger_service.get_summary(
        db, org_id, from_date=from_date, to_date=to_date
    )
