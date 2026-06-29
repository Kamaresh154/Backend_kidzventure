import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.types import UuidType


class Role(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions", back_populates="roles"
    )


class Permission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary="role_permissions", back_populates="permissions"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UuidType,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=True,
    )
    center_id: Mapped[uuid.UUID | None] = mapped_column(
        UuidType,
        ForeignKey("centers.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=True,
    )

    role: Mapped["Role"] = relationship()
