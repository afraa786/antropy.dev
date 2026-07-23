import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appsec.config import get_settings
from appsec.infrastructure.db.models.scan_job import ScanJobModel


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SECRET_KEY", "full_name": None},
    )
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_quick_scan_happy_path_with_skip_verification(
    client: AsyncClient, db_session: AsyncSession, random_email: str
) -> None:
    # skip_verification is guarded by this env flag; enable it for the test.
    get_settings.cache_clear()
    with (
        patch.object(get_settings(), "allow_demo_verification_skip", True),
        patch("appsec.application.scan_jobs.service.execute_scan_job.delay") as mock_delay,
    ):
        access_token = await _register_login(client, random_email)
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await client.post(
            "/api/v1/quick-scan",
            json={
                "target": "example.com",
                "target_type": "domain",
                "skip_verification": True,
            },
            headers=headers,
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    scan_job_id = uuid.UUID(body["scan_job_id"])  # valid UUID

    # The scan job row actually exists in the DB.
    result = await db_session.execute(select(ScanJobModel).where(ScanJobModel.id == scan_job_id))
    scan_job = result.scalar_one_or_none()
    assert scan_job is not None
    assert scan_job.scan_type == "default"

    # The scan was actually enqueued for execution.
    mock_delay.assert_called_once_with(str(scan_job_id))


@pytest.mark.asyncio
async def test_quick_scan_skip_rejected_when_flag_disabled(client: AsyncClient, random_email: str) -> None:
    get_settings.cache_clear()
    with patch.object(get_settings(), "allow_demo_verification_skip", False):
        access_token = await _register_login(client, random_email)
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await client.post(
            "/api/v1/quick-scan",
            json={"target": "example.com", "skip_verification": True},
            headers=headers,
        )

    assert response.status_code == 403
