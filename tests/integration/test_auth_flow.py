import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient, random_email: str) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": random_email, "password": "supersecret123", "full_name": "Test User"},
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == random_email

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": random_email, "password": "supersecret123"}
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client: AsyncClient, random_email: str) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": random_email, "password": "supersecret123", "full_name": None},
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": random_email, "password": "wrongpassword"}
    )
    assert response.status_code == 401
