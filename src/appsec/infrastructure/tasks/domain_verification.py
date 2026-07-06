from datetime import UTC, datetime

import httpx

from appsec.config import get_settings
from appsec.domain.enums import VerificationMethod, VerificationStatus
from appsec.infrastructure.celery_app import celery_app
from appsec.infrastructure.db.models.domain import DomainModel
from appsec.infrastructure.db.sync_session import get_sync_session
from appsec.infrastructure.external.dns_client import resolve_txt_records
from appsec.logging import get_logger

logger = get_logger(__name__)


def _expected_txt_value(token: str) -> str:
    settings = get_settings()
    return f"{settings.verification_token_prefix}={token}"


def _check_dns_txt(hostname: str, token: str) -> bool:
    expected = _expected_txt_value(token)
    records = resolve_txt_records(hostname)
    return expected in records


def _check_http_file(hostname: str, token: str) -> bool:
    settings = get_settings()
    url = f"http://{hostname}/.well-known/{settings.verification_token_prefix}/{token}.txt"
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True)
    except httpx.HTTPError:
        return False
    return response.status_code == 200 and response.text.strip() == token


@celery_app.task(name="domain_verification.check", bind=True, max_retries=3)
def check_domain_verification(self, domain_id: str) -> bool:
    with get_sync_session() as session:
        domain = session.get(DomainModel, domain_id)
        if domain is None:
            logger.warning("domain_not_found", domain_id=domain_id)
            return False

        if domain.verification_method == VerificationMethod.DNS_TXT:
            verified = _check_dns_txt(domain.hostname, domain.verification_token)
        else:
            verified = _check_http_file(domain.hostname, domain.verification_token)

        domain.verification_status = (
            VerificationStatus.VERIFIED if verified else VerificationStatus.FAILED
        )
        if verified:
            domain.verified_at = datetime.now(UTC)
        session.commit()

        logger.info(
            "domain_verification_checked",
            domain_id=domain_id,
            hostname=domain.hostname,
            verified=verified,
        )
        return verified
