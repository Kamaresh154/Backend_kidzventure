"""Franchise service — super admin cross-org view."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.ledger import LedgerAccount, LedgerEntry
from app.models.organization import Center, Organization
from app.models.student import Student
from app.models.user import User
from app.models.rbac import UserRole, Role


async def list_all_organizations(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """List all orgs with quick stats — super admin only."""
    q = select(Organization).where(Organization.deleted_at.is_(None))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    orgs = (
        await db.execute(q.order_by(Organization.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    result = []
    for org in orgs:
        student_count = (
            await db.execute(
                select(func.count()).select_from(Student).where(
                    Student.organization_id == org.id, Student.deleted_at.is_(None)
                )
            )
        ).scalar_one()
        center_count = (
            await db.execute(
                select(func.count()).select_from(Center).where(
                    Center.organization_id == org.id, Center.deleted_at.is_(None)
                )
            )
        ).scalar_one()
        result.append({
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "student_count": student_count,
            "center_count": center_count,
            "created_at": org.created_at.isoformat() if org.created_at else None,
        })
    return result, total


async def get_org_stats(db: AsyncSession, org_id: uuid.UUID) -> dict:
    """Detailed stats for one org — franchise dashboard."""
    org = (
        await db.execute(select(Organization).where(Organization.id == org_id))
    ).scalar_one_or_none()
    if not org:
        return {}

    student_count = (
        await db.execute(
            select(func.count()).select_from(Student).where(
                Student.organization_id == org_id, Student.deleted_at.is_(None)
            )
        )
    ).scalar_one()

    center_count = (
        await db.execute(
            select(func.count()).select_from(Center).where(
                Center.organization_id == org_id, Center.deleted_at.is_(None)
            )
        )
    ).scalar_one()

    revenue = (
        await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(LedgerAccount, LedgerEntry.account_id == LedgerAccount.id)
            .where(
                LedgerEntry.organization_id == org_id,
                LedgerEntry.direction == "credit",
                LedgerAccount.account_type == "revenue",
            )
        )
    ).scalar_one()

    pending_invoices = (
        await db.execute(
            select(func.count()).select_from(Invoice).where(
                Invoice.organization_id == org_id,
                Invoice.status.in_(["sent", "overdue"]),
            )
        )
    ).scalar_one()

    return {
        "org_id": str(org_id),
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "student_count": student_count,
        "center_count": center_count,
        "total_revenue": float(revenue),
        "pending_invoices": pending_invoices,
    }


async def get_cross_franchise_summary(db: AsyncSession) -> dict:
    """Global summary across all orgs — super admin dashboard."""
    total_orgs = (
        await db.execute(select(func.count()).select_from(Organization).where(Organization.deleted_at.is_(None)))
    ).scalar_one()

    total_students = (
        await db.execute(select(func.count()).select_from(Student).where(Student.deleted_at.is_(None)))
    ).scalar_one()

    total_revenue = (
        await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(LedgerAccount, LedgerEntry.account_id == LedgerAccount.id)
            .where(LedgerEntry.direction == "credit", LedgerAccount.account_type == "revenue")
        )
    ).scalar_one()

    return {
        "total_franchises": total_orgs,
        "total_students": total_students,
        "total_revenue": float(total_revenue),
    }
