"""
reset_db.py — Wipe ALL data from KidzVenture SQLite database
and keep ONLY the Super Admin account.

Usage:
    python reset_db.py

After reset:
    Super Admin Email:    superadmin@kidzventure.com
    Super Admin Password: SuperAdmin@123
"""

import asyncio
import os
import sys

# Make sure we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set env so app uses SQLite
os.environ.setdefault("DEV_SQLITE", "true")
os.environ.setdefault("SQLITE_PATH", "./kidzventure_dev.db")
os.environ.setdefault("JWT_SECRET", "dev-secret-kidzventure-local")

from sqlalchemy import text, delete, select
from app.core.database import engine, AsyncSessionLocal
from app.models.base import Base
from app.models.user import User
from app.models.rbac import Role, Permission, RolePermission, UserRole
from app.models.organization import Organization, Center
from app.core.security import hash_password


# ── Tables to wipe (order matters for FK constraints) ──────────────────────
WIPE_TABLES = [
    # CRM
    "crm_leads", "crm_activities",
    # Payroll / HR
    "payslips", "salary_structures",
    # Inventory / Orders
    "inventory_transactions", "inventory_items",
    # Ledger / Finance
    "ledger_entries",
    # Invoices
    "invoice_items", "invoices",
    # Attendance
    "attendance_records",
    # Students / Parents
    "student_parents", "students", "parents",
    # Centers & Orgs (except roles/perms/super admin)
    "centers", "organizations",
    # Users (all except super admin — handled specially)
    "user_roles", "users",
]

SUPER_ADMIN_EMAIL = "superadmin@kidzventure.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin@123"
SUPER_ADMIN_NAME = "Super Admin"


async def reset():
    print("=" * 55)
    print("  KidzVenture DB Reset")
    print("=" * 55)

    async with engine.begin() as conn:
        # Disable FK checks for SQLite
        await conn.execute(text("PRAGMA foreign_keys = OFF"))

        for table in WIPE_TABLES:
            try:
                await conn.execute(text(f"DELETE FROM {table}"))
                print(f"  ✓ Cleared: {table}")
            except Exception as e:
                print(f"  ⚠ Skipped {table}: {e}")

        # Re-enable FK checks
        await conn.execute(text("PRAGMA foreign_keys = ON"))

    print("\n  Recreating Super Admin account...")

    async with AsyncSessionLocal() as db:
        # Ensure roles & permissions exist
        existing_role = (await db.execute(select(Role).where(Role.code == "super_admin"))).scalar_one_or_none()
        if not existing_role:
            from app.db.bootstrap import seed_rbac
            await seed_rbac(db)
            await db.flush()

        # Create super admin user
        sa_user = User(
            organization_id=None,
            email=SUPER_ADMIN_EMAIL,
            password_hash=hash_password(SUPER_ADMIN_PASSWORD),
            full_name=SUPER_ADMIN_NAME,
            status="active",
        )
        db.add(sa_user)
        await db.flush()

        sa_role = (await db.execute(select(Role).where(Role.code == "super_admin"))).scalar_one()
        db.add(UserRole(user_id=sa_user.id, role_id=sa_role.id, organization_id=None, center_id=None))
        await db.commit()

    print("\n" + "=" * 55)
    print("  ✅ Reset complete!")
    print("=" * 55)
    print(f"\n  Super Admin Email   : {SUPER_ADMIN_EMAIL}")
    print(f"  Super Admin Password: {SUPER_ADMIN_PASSWORD}")
    print("\n  ⚠  Change the password after first login!")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(reset())
