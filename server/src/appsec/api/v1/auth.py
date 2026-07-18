from typing import Annotated

from fastapi import APIRouter, Depends, status

from appsec.api.deps import get_auth_service
from appsec.application.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from appsec.application.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserResponse:
    user = await auth_service.register(payload.email, payload.password, payload.full_name)
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenPairResponse:
    access_token, refresh_token = await auth_service.login(payload.email, payload.password)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenPairResponse:
    access_token, refresh_token = await auth_service.refresh(payload.refresh_token)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> None:
    await auth_service.logout(payload.refresh_token)
