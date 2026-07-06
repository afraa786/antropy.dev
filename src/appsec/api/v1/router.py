from fastapi import APIRouter

from appsec.api.v1 import (
    auth,
    domains,
    health,
    notifications,
    organizations,
    projects,
    reports,
    scan_jobs,
    scan_results,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(projects.router)
api_router.include_router(domains.router)
api_router.include_router(scan_jobs.router)
api_router.include_router(scan_results.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
