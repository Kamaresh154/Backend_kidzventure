"""Payroll models — staff salary, deductions, bonuses, payslips."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonType, UuidType


class StaffProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """HR profile linked to a user (teacher, accountant, branch_manager, etc.)."""

    __tablename__ = "staff_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("centers.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    employee_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date, nullable=True)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    bank_account: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    payslips: Mapped[list["Payslip"]] = relationship(back_populates="staff")


class Payslip(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Monthly payslip for one staff member."""

    __tablename__ = "payslips"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False
    )
    pay_period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    allowances: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    bonus: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)  # draft | approved | paid
    breakdown: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    staff: Mapped["StaffProfile"] = relationship(back_populates="payslips")
