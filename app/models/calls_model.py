"""Call logs and appointments models."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import UuidType


class CallLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "call_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_secs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    call_direction: Mapped[str] = mapped_column(String(16), default="outbound", nullable=False)
    sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    centre_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    centre_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recording_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    call_sid: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class Appointment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "appointments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    appt_type: Mapped[str] = mapped_column(String(64), default="other", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
