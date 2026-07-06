import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.application.auth.service import AuthService
from appsec.application.domains.service import DomainService
from appsec.application.notifications.service import NotificationService
from appsec.application.organizations.service import OrganizationService
from appsec.application.projects.service import ProjectService
from appsec.application.reports.service import ReportService
from appsec.application.scan_jobs.service import ScanJobService
from appsec.application.scan_results.service import ScanResultService
from appsec.application.users.service import UserService
from appsec.domain.exceptions import ForbiddenError, UnauthorizedError
from appsec.infrastructure.db.repositories.domain_repository import SqlAlchemyDomainRepository
from appsec.infrastructure.db.repositories.notification_repository import (
    SqlAlchemyNotificationRepository,
)
from appsec.infrastructure.db.repositories.organization_repository import (
    SqlAlchemyOrganizationRepository,
)
from appsec.infrastructure.db.repositories.project_repository import SqlAlchemyProjectRepository
from appsec.infrastructure.db.repositories.report_repository import SqlAlchemyReportRepository
from appsec.infrastructure.db.repositories.scan_job_repository import SqlAlchemyScanJobRepository
from appsec.infrastructure.db.repositories.scan_result_repository import (
    SqlAlchemyScanResultRepository,
)
from appsec.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository
from appsec.infrastructure.db.session import get_session
from appsec.infrastructure.redis_client import get_redis
from appsec.infrastructure.security.jwt import decode_token
from appsec.infrastructure.security.redis_blacklist import TokenBlacklist

_bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    yield get_redis()


RedisDep = Annotated[Redis, Depends(get_redis_client)]


def get_token_blacklist(redis: RedisDep) -> TokenBlacklist:
    return TokenBlacklist(redis)


TokenBlacklistDep = Annotated[TokenBlacklist, Depends(get_token_blacklist)]


def get_user_repository(session: SessionDep) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def get_organization_repository(session: SessionDep) -> SqlAlchemyOrganizationRepository:
    return SqlAlchemyOrganizationRepository(session)


def get_project_repository(session: SessionDep) -> SqlAlchemyProjectRepository:
    return SqlAlchemyProjectRepository(session)


def get_domain_repository(session: SessionDep) -> SqlAlchemyDomainRepository:
    return SqlAlchemyDomainRepository(session)


def get_scan_job_repository(session: SessionDep) -> SqlAlchemyScanJobRepository:
    return SqlAlchemyScanJobRepository(session)


def get_scan_result_repository(session: SessionDep) -> SqlAlchemyScanResultRepository:
    return SqlAlchemyScanResultRepository(session)


def get_report_repository(session: SessionDep) -> SqlAlchemyReportRepository:
    return SqlAlchemyReportRepository(session)


def get_notification_repository(session: SessionDep) -> SqlAlchemyNotificationRepository:
    return SqlAlchemyNotificationRepository(session)


def get_auth_service(
    session: SessionDep,
    user_repository: Annotated[SqlAlchemyUserRepository, Depends(get_user_repository)],
    token_blacklist: TokenBlacklistDep,
) -> AuthService:
    return AuthService(session, user_repository, token_blacklist)


def get_user_service(
    session: SessionDep,
    user_repository: Annotated[SqlAlchemyUserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(session, user_repository)


def get_organization_service(
    session: SessionDep,
    organization_repository: Annotated[
        SqlAlchemyOrganizationRepository, Depends(get_organization_repository)
    ],
) -> OrganizationService:
    return OrganizationService(session, organization_repository)


def get_project_service(
    session: SessionDep,
    project_repository: Annotated[SqlAlchemyProjectRepository, Depends(get_project_repository)],
    organization_repository: Annotated[
        SqlAlchemyOrganizationRepository, Depends(get_organization_repository)
    ],
) -> ProjectService:
    return ProjectService(session, project_repository, organization_repository)


def get_domain_service(
    session: SessionDep,
    domain_repository: Annotated[SqlAlchemyDomainRepository, Depends(get_domain_repository)],
    project_repository: Annotated[SqlAlchemyProjectRepository, Depends(get_project_repository)],
    organization_repository: Annotated[
        SqlAlchemyOrganizationRepository, Depends(get_organization_repository)
    ],
) -> DomainService:
    return DomainService(session, domain_repository, project_repository, organization_repository)


def get_scan_job_service(
    session: SessionDep,
    scan_job_repository: Annotated[SqlAlchemyScanJobRepository, Depends(get_scan_job_repository)],
    domain_repository: Annotated[SqlAlchemyDomainRepository, Depends(get_domain_repository)],
    project_repository: Annotated[SqlAlchemyProjectRepository, Depends(get_project_repository)],
    organization_repository: Annotated[
        SqlAlchemyOrganizationRepository, Depends(get_organization_repository)
    ],
) -> ScanJobService:
    return ScanJobService(
        session, scan_job_repository, domain_repository, project_repository, organization_repository
    )


def get_scan_result_service(
    scan_result_repository: Annotated[
        SqlAlchemyScanResultRepository, Depends(get_scan_result_repository)
    ],
    organization_repository: Annotated[
        SqlAlchemyOrganizationRepository, Depends(get_organization_repository)
    ],
) -> ScanResultService:
    return ScanResultService(scan_result_repository, organization_repository)


def get_report_service(
    session: SessionDep,
    report_repository: Annotated[SqlAlchemyReportRepository, Depends(get_report_repository)],
    scan_job_repository: Annotated[SqlAlchemyScanJobRepository, Depends(get_scan_job_repository)],
    organization_repository: Annotated[
        SqlAlchemyOrganizationRepository, Depends(get_organization_repository)
    ],
) -> ReportService:
    return ReportService(session, report_repository, scan_job_repository, organization_repository)


def get_notification_service(
    session: SessionDep,
    notification_repository: Annotated[
        SqlAlchemyNotificationRepository, Depends(get_notification_repository)
    ],
) -> NotificationService:
    return NotificationService(session, notification_repository)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    token_blacklist: TokenBlacklistDep,
) -> uuid.UUID:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    payload = decode_token(credentials.credentials)
    if payload.type != "access":
        raise UnauthorizedError("Invalid token type")
    if await token_blacklist.is_revoked(payload.jti):
        raise UnauthorizedError("Token has been revoked")
    return payload.sub


CurrentUserIdDep = Annotated[uuid.UUID, Depends(get_current_user_id)]


async def get_current_organization_id(
    x_organization_id: Annotated[str | None, Header()] = None,
) -> uuid.UUID:
    if x_organization_id is None:
        raise ForbiddenError("X-Organization-ID header is required")
    try:
        return uuid.UUID(x_organization_id)
    except ValueError as exc:
        raise ForbiddenError("Invalid X-Organization-ID header") from exc


CurrentOrganizationIdDep = Annotated[uuid.UUID, Depends(get_current_organization_id)]
