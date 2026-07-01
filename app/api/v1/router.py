from fastapi import APIRouter

from app.api.v1 import (
    attendance, attendance_emp, auth, calls_api, crm, franchise, inventory,
    invoices, leaves, ledger, orders_api, organizations, parents, payroll,
    quotations_api, reports, students, users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(students.router)
api_router.include_router(parents.router)
api_router.include_router(attendance.router)
api_router.include_router(attendance_emp.router)
api_router.include_router(inventory.router)
api_router.include_router(invoices.router)
api_router.include_router(ledger.router)
api_router.include_router(payroll.router)
api_router.include_router(crm.router)
api_router.include_router(leaves.router)
api_router.include_router(orders_api.router)
api_router.include_router(quotations_api.router)
api_router.include_router(reports.router)
api_router.include_router(franchise.router)
api_router.include_router(users.router)
api_router.include_router(calls_api.router)
