"""Tele calling & appointments API."""
from datetime import datetime, timezone
import re
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUserDep, DbSession, resolve_org_id
from app.models.calls_model import Appointment, CallLog

router = APIRouter(prefix="/calls", tags=["calls"])


# ── Schemas ────────────────────────────────────────────────────────────────

class CallLogCreate(BaseModel):
    customer_name: str
    phone: str
    agent_name: str | None = None
    duration_secs: int = 0
    status: str = "completed"
    call_direction: str = "outbound"
    sector: str | None = None
    centre_id: str | None = None
    centre_name: str | None = None
    recording_source: str | None = None
    notes: str | None = None
    recording_url: str | None = None
    started_at: datetime | None = None


class CallLogResponse(BaseModel):
    id: UUID
    customer_name: str
    phone: str
    agent_name: str | None
    started_at: datetime
    duration_secs: int
    status: str
    call_direction: str
    sector: str | None
    centre_id: str | None
    centre_name: str | None
    recording_source: str | None
    notes: str | None
    recording_url: str | None

    class Config:
        from_attributes = True


class ExotelCallCreate(BaseModel):
    customer_name: str
    to_number: str
    agent_number: str
    sector: str | None = None
    centre_name: str | None = None
    notes: str | None = None


class ExotelCallResponse(BaseModel):
    call_sid: str
    status: str
    log_id: UUID


class ExotelStatusResponse(BaseModel):
    call_sid: str
    status: str
    recording_url: str | None = None
    duration_secs: int = 0
    log_id: UUID | None = None


class AppointmentCreate(BaseModel):
    title: str | None = None
    customer_name: str
    phone: str | None = None
    assigned_name: str | None = None
    appointment_at: datetime
    appt_type: str = "other"
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    title: str | None = None
    customer_name: str | None = None
    phone: str | None = None
    assigned_name: str | None = None
    appointment_at: datetime | None = None
    appt_type: str | None = None
    status: str | None = None
    notes: str | None = None


class AppointmentResponse(BaseModel):
    id: UUID
    title: str | None
    customer_name: str
    phone: str | None
    assigned_name: str | None
    appointment_at: datetime
    appt_type: str
    status: str
    notes: str | None

    class Config:
        from_attributes = True


def _normalize_indian_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    raise HTTPException(422, "Enter a valid 10-digit Indian phone number.")


def _exotel_config() -> tuple[str, str, str, str]:
    values = (
        settings.exotel_account_sid,
        settings.exotel_api_key,
        settings.exotel_api_token,
        settings.exotel_caller_id,
    )
    if not all(values):
        raise HTTPException(503, "Exotel is not configured on the backend.")
    return values


def _call_payload(data: dict) -> dict:
    call = data.get("Call")
    return call if isinstance(call, dict) else data


def _provider_error(response: httpx.Response) -> str:
    try:
        data = response.json()
        message = data.get("message") or data.get("Message")
        if message:
            return str(message)
        rest_exception = data.get("RestException")
        if isinstance(rest_exception, dict):
            return str(
                rest_exception.get("Message")
                or rest_exception.get("message")
                or "Exotel rejected the call."
            )
        error = data.get("Error")
        if isinstance(error, dict):
            return str(error.get("Message") or error.get("message") or "Exotel rejected the call.")
    except ValueError:
        pass
    return f"Exotel rejected the call (HTTP {response.status_code})."


# ── Call Logs ──────────────────────────────────────────────────────────────

@router.get("/logs", response_model=list[CallLogResponse])
async def list_calls(
    db: DbSession, current: CurrentUserDep,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> list[CallLogResponse]:
    org = await resolve_org_id(current, db)
    result = await db.execute(
        select(CallLog).where(CallLog.organization_id == org)
        .order_by(CallLog.started_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return [CallLogResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/logs", response_model=CallLogResponse, status_code=201)
async def create_call_log(data: CallLogCreate, db: DbSession, current: CurrentUserDep) -> CallLogResponse:
    org = await resolve_org_id(current, db)
    log = CallLog(
        organization_id=org,
        customer_name=data.customer_name,
        phone=data.phone,
        agent_id=current.user.id,
        agent_name=data.agent_name or current.user.full_name,
        started_at=data.started_at or datetime.now(timezone.utc),
        duration_secs=data.duration_secs,
        status=data.status,
        call_direction=data.call_direction,
        sector=data.sector,
        centre_id=data.centre_id,
        centre_name=data.centre_name,
        recording_source=data.recording_source,
        notes=data.notes,
        recording_url=data.recording_url,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return CallLogResponse.model_validate(log)


@router.post("/exotel/initiate", response_model=ExotelCallResponse, status_code=201)
async def initiate_exotel_call(
    data: ExotelCallCreate, db: DbSession, current: CurrentUserDep
) -> ExotelCallResponse:
    org = await resolve_org_id(current, db)
    account_sid, api_key, api_token, caller_id = _exotel_config()
    agent_number = _normalize_indian_phone(data.agent_number)
    customer_number = _normalize_indian_phone(data.to_number)
    endpoint = (
        f"{settings.exotel_api_base_url.rstrip('/')}/v1/Accounts/"
        f"{account_sid}/Calls/connect.json"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                endpoint,
                auth=(api_key, api_token),
                data={
                    "From": agent_number,
                    "To": customer_number,
                    "CallerId": caller_id,
                    "Record": "true",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(502, "Could not connect to Exotel.") from exc

    if response.is_error:
        raise HTTPException(response.status_code, _provider_error(response))

    try:
        provider_call = _call_payload(response.json())
    except ValueError as exc:
        raise HTTPException(502, "Exotel returned an invalid response.") from exc

    call_sid = str(provider_call.get("Sid") or provider_call.get("sid") or "")
    if not call_sid:
        raise HTTPException(502, "Exotel did not return a call ID.")

    status = str(provider_call.get("Status") or provider_call.get("status") or "initiated")
    log = CallLog(
        organization_id=org,
        customer_name=data.customer_name.strip(),
        phone=customer_number,
        agent_id=current.user.id,
        agent_name=current.user.full_name,
        started_at=datetime.now(timezone.utc),
        status=status,
        call_direction="outbound",
        sector=data.sector,
        centre_name=data.centre_name,
        recording_source="exotel",
        call_sid=call_sid,
        notes=data.notes,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return ExotelCallResponse(call_sid=call_sid, status=status, log_id=log.id)


@router.get("/exotel/status/{call_sid}", response_model=ExotelStatusResponse)
async def get_exotel_call_status(
    call_sid: str, db: DbSession, current: CurrentUserDep
) -> ExotelStatusResponse:
    org = await resolve_org_id(current, db)
    account_sid, api_key, api_token, _caller_id = _exotel_config()
    log = (
        await db.execute(
            select(CallLog).where(
                CallLog.organization_id == org,
                CallLog.call_sid == call_sid,
            )
        )
    ).scalar_one_or_none()
    if not log:
        raise HTTPException(404, "Call log not found.")

    endpoint = (
        f"{settings.exotel_api_base_url.rstrip('/')}/v1/Accounts/"
        f"{account_sid}/Calls/{call_sid}.json"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(endpoint, auth=(api_key, api_token))
    except httpx.RequestError as exc:
        raise HTTPException(502, "Could not connect to Exotel.") from exc

    if response.is_error:
        raise HTTPException(response.status_code, _provider_error(response))

    try:
        provider_call = _call_payload(response.json())
    except ValueError as exc:
        raise HTTPException(502, "Exotel returned an invalid response.") from exc

    status = str(provider_call.get("Status") or provider_call.get("status") or log.status)
    recording_url = (
        provider_call.get("RecordingUrl")
        or provider_call.get("recording_url")
        or log.recording_url
    )
    raw_duration = provider_call.get("Duration") or provider_call.get("duration") or 0
    try:
        duration_secs = int(raw_duration)
    except (TypeError, ValueError):
        duration_secs = 0

    log.status = status
    log.recording_url = recording_url
    log.duration_secs = duration_secs
    if status in {"completed", "failed", "busy", "no-answer", "canceled"}:
        log.ended_at = datetime.now(timezone.utc)
    await db.commit()

    return ExotelStatusResponse(
        call_sid=call_sid,
        status=status,
        recording_url=recording_url,
        duration_secs=duration_secs,
        log_id=log.id,
    )


# ── Appointments ───────────────────────────────────────────────────────────

@router.get("/appointments", response_model=list[AppointmentResponse])
async def list_appointments(
    db: DbSession, current: CurrentUserDep,
    status: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
) -> list[AppointmentResponse]:
    org = await resolve_org_id(current, db)
    q = select(Appointment).where(
        Appointment.organization_id == org,
        Appointment.deleted_at.is_(None),
    )
    if status:
        q = q.where(Appointment.status == status)
    result = await db.execute(q.order_by(Appointment.appointment_at.asc()).offset((page - 1) * page_size).limit(page_size))
    return [AppointmentResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
async def create_appointment(data: AppointmentCreate, db: DbSession, current: CurrentUserDep) -> AppointmentResponse:
    org = await resolve_org_id(current, db)
    appt = Appointment(organization_id=org, **data.model_dump())
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return AppointmentResponse.model_validate(appt)


@router.patch("/appointments/{appt_id}", response_model=AppointmentResponse)
async def update_appointment(appt_id: UUID, data: AppointmentUpdate, db: DbSession, current: CurrentUserDep) -> AppointmentResponse:
    org = await resolve_org_id(current, db)
    appt = (await db.execute(
        select(Appointment).where(Appointment.id == appt_id, Appointment.organization_id == org, Appointment.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Appointment not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(appt, k, v)
    await db.commit()
    await db.refresh(appt)
    return AppointmentResponse.model_validate(appt)


@router.delete("/appointments/{appt_id}", status_code=204)
async def delete_appointment(appt_id: UUID, db: DbSession, current: CurrentUserDep) -> None:
    org = await resolve_org_id(current, db)
    appt = (await db.execute(
        select(Appointment).where(Appointment.id == appt_id, Appointment.organization_id == org, Appointment.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Appointment not found")
    appt.deleted_at = datetime.now(timezone.utc)
    await db.commit()
