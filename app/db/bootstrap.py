import app.models.calls_model  # ensure tables are registered
"""Initialize SQLite dev DB with schema, RBAC, and demo data."""

from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.base import Base
from app.models.organization import Center, Organization
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.core.database import engine


ROLE_SEEDS = [
    ("super_admin", "Super Admin"),
    ("franchise_owner", "Franchise Owner"),
    ("franchise_manager", "Franchise Manager"),
    ("employee", "Employee"),
    ("branch_manager", "Branch Manager"),
    ("accountant", "Accountant"),
    ("staff", "Staff"),
    ("teacher", "Teacher"),
    ("parent", "Parent"),
    ("student", "Student"),
]

PERM_SEEDS = [
    ("organizations.read", "organizations"),
    ("organizations.write", "organizations"),
    ("centers.read", "centers"),
    ("centers.write", "centers"),
    ("students.read", "students"),
    ("students.write", "students"),
    ("users.read", "users"),
    ("users.write", "users"),
    ("auth.manage", "auth"),
    ("parents.read", "parents"),
    ("parents.write", "parents"),
    ("attendance.read", "attendance"),
    ("attendance.write", "attendance"),
    ("invoices.read", "invoices"),
    ("invoices.write", "invoices"),
    ("ledger.read", "ledger"),
    ("ledger.write", "ledger"),
    # Phase 4
    ("payroll.read", "payroll"),
    ("payroll.write", "payroll"),
    ("inventory.read", "inventory"),
    ("inventory.write", "inventory"),
    ("crm.read", "crm"),
    ("crm.write", "crm"),
    ("reports.read", "reports"),
    ("franchise.read", "franchise"),
]

OWNER_PERMS = {
    "organizations.read", "organizations.write",
    "centers.read", "centers.write",
    "students.read", "students.write",
    "users.read", "users.write",
    "parents.read", "parents.write",
    "attendance.read", "attendance.write",
    "invoices.read", "invoices.write",
    "ledger.read", "ledger.write",
    "payroll.read", "payroll.write",
    "inventory.read", "inventory.write",
    "crm.read", "crm.write",
    "reports.read",
    "franchise.read",
}


async def init_sqlite_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def get_call_log_columns(sync_conn) -> set[str]:
            return {
                column["name"]
                for column in inspect(sync_conn).get_columns("call_logs")
            }

        columns = await conn.run_sync(get_call_log_columns)
        if "call_sid" not in columns:
            await conn.execute(text("ALTER TABLE call_logs ADD COLUMN call_sid VARCHAR(255)"))
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_call_logs_call_sid "
                    "ON call_logs (call_sid)"
                )
            )


async def seed_rbac(db: AsyncSession) -> None:
    existing = await db.execute(select(Role).limit(1))
    if existing.scalar_one_or_none():
        return

    roles: dict[str, Role] = {}
    for code, name in ROLE_SEEDS:
        role = Role(code=code, name=name)
        db.add(role)
        roles[code] = role
    await db.flush()

    perms: dict[str, Permission] = {}
    for code, module in PERM_SEEDS:
        perm = Permission(code=code, module=module)
        db.add(perm)
        perms[code] = perm
    await db.flush()

    for code in OWNER_PERMS:
        db.add(RolePermission(role_id=roles["franchise_owner"].id, permission_id=perms[code].id))

    # employee: read-only access for payroll, attendance, crm
    EMPLOYEE_PERMS = {
        "organizations.read", "centers.read",
        "attendance.read", "attendance.write",
        "payroll.read", "crm.read", "crm.write",
        "invoices.read", "inventory.read", "reports.read",
    }
    if "employee" in roles:
        for code in EMPLOYEE_PERMS:
            if code in perms:
                db.add(RolePermission(role_id=roles["employee"].id, permission_id=perms[code].id))

    # franchise_manager: same as franchise_owner
    if "franchise_manager" in roles:
        for code in OWNER_PERMS:
            if code in perms:
                db.add(RolePermission(role_id=roles["franchise_manager"].id, permission_id=perms[code].id))


async def seed_demo_org(db: AsyncSession) -> None:
    existing = await db.execute(select(Organization).where(Organization.slug == "demo"))
    if existing.scalar_one_or_none():
        return

    org = Organization(name="Demo Learning Center", slug="demo")
    db.add(org)
    await db.flush()

    db.add(Center(organization_id=org.id, name="Main Campus", code="MAIN"))

    user = User(
        organization_id=org.id,
        email="admin@demo.kidzventure.com",
        password_hash=hash_password("Admin@123"),
        full_name="Demo Admin",
        status="active",
    )
    db.add(user)
    await db.flush()

    role = (await db.execute(select(Role).where(Role.code == "franchise_owner"))).scalar_one()
    db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id, center_id=None))

    # Seed super admin
    existing_sa = await db.execute(select(User).where(User.email == "superadmin@kidzventure.com"))
    if not existing_sa.scalar_one_or_none():
        sa_user = User(
            organization_id=None,
            email="superadmin@kidzventure.com",
            password_hash=hash_password("SuperAdmin@123"),
            full_name="Super Admin",
            status="active",
        )
        db.add(sa_user)
        await db.flush()
        sa_role = (await db.execute(select(Role).where(Role.code == "super_admin"))).scalar_one()
        db.add(UserRole(user_id=sa_user.id, role_id=sa_role.id, organization_id=None, center_id=None))


async def bootstrap_sqlite() -> None:
    await init_sqlite_schema()
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await seed_rbac(db)
        await seed_demo_org(db)
        await db.commit()
