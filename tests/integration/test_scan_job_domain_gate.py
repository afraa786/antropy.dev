import pytest
from httpx import AsyncClient


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret123", "full_name": None}
    )
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_scan_job_blocked_until_domain_verified(client: AsyncClient, random_email: str) -> None:
    access_token = await _register_login(client, random_email)
    headers = {"Authorization": f"Bearer {access_token}"}

    org_response = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme Corp", "slug": "acme-corp"},
        headers=headers,
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]
    headers["X-Organization-ID"] = org_id

    project_response = await client.post(
        "/api/v1/projects", json={"name": "Main Site", "description": None}, headers=headers
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    domain_response = await client.post(
        f"/api/v1/projects/{project_id}/domains",
        json={"hostname": "example.com", "verification_method": "dns_txt"},
        headers=headers,
    )
    assert domain_response.status_code == 201
    domain_id = domain_response.json()["id"]
    assert domain_response.json()["verification_status"] == "pending"

    scan_job_response = await client.post(
        f"/api/v1/projects/{project_id}/scan-jobs",
        json={"domain_id": domain_id, "scan_type": "default"},
        headers=headers,
    )
    assert scan_job_response.status_code == 403
    assert scan_job_response.json()["error"]["code"] == "domain_not_verified"
