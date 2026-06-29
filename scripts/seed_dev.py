"""Seed a demo organization and admin user. Run from backend/: python -m scripts.seed_dev

The admin password is read from the SEED_ADMIN_PASSWORD environment variable.
If not set, a random password will be generated and printed once.
"""

import asyncio
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.organization import Center, Organization
from app.models.rbac import Role, UserRole
from app.models.user import User


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Organization).where(Organization.slug == "demo"))
        if existing.scalar_one_or_none():
            print("Demo org already exists (slug: demo)")
            return

        # Use env var or generate a one-time random password
        admin_password = os.environ.get("SEED_ADMIN_PASSWORD") or secrets.token_urlsafe(16)

        org = Organization(name="Demo Learning Center", slug="demo")
        db.add(org)
        await db.flush()

        center = Center(organization_id=org.id, name="Main Campus", code="MAIN")
        db.add(center)

        user = User(
            organization_id=org.id,
            email="admin@demo.kidzventure.local",
            password_hash=hash_password(admin_password),
            full_name="Demo Admin",
            status="active",
        )
        db.add(user)
        await db.flush()

        role = (await db.execute(select(Role).where(Role.code == "franchise_owner"))).scalar_one()
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id, center_id=None))

        await db.commit()
        print("Seeded demo org:")
        print("  slug: demo")
        print("  email: admin@demo.kidzventure.local")
        print(f"  password: {admin_password}")
        if not os.environ.get("SEED_ADMIN_PASSWORD"):
            print("  (auto-generated — store this password securely, it won't be shown again)")


if __name__ == "__main__":
    asyncio.run(main())
