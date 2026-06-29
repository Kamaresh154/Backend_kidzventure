"""CRM — leads, enquiries, enrolment pipeline."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import UuidType


class Lead(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Enquiry / lead — a potential student/parent."""

    __tablename__ = "leads"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("centers.id", ondelete="SET NULL"), nullable=True
    )
    child_name: Mapped[str] = mapped_column(String(255), nullable=False)
    child_age: Mapped[int | None] = mapped_column(nullable=True)
    parent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # walk-in | referral | social | ad
    status: Mapped[str] = mapped_column(
        String(32), default="new", nullable=False
    )  # new | contacted | trial_scheduled | trial_done | enrolled | lost
    lost_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_student_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )

    activities: Mapped[list["LeadActivity"]] = relationship(back_populates="lead")


class LeadActivity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Activity log entry on a lead."""

    __tablename__ = "lead_activities"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)  # call | email | sms | meeting | note | status_change
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    lead: Mapped["Lead"] = relationship(back_populates="activities")
