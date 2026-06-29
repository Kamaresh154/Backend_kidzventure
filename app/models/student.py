import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonType, UuidType


class Parent(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Batch(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "batches"

    center_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("centers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)


class Student(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("centers.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType, ForeignKey("batches.id", ondelete="SET NULL"), nullable=True
    )
    admission_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qr_code: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    medical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class StudentParent(Base):
    __tablename__ = "student_parents"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("parents.id", ondelete="CASCADE"), primary_key=True
    )
    relationship: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
