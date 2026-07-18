from typing import Annotated

from fastapi import APIRouter, Depends

from appsec.api.deps import CurrentUserIdDep, get_user_service
from appsec.application.users.schemas import UpdateUserRequest, UserProfileResponse
from appsec.application.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    user_id: CurrentUserIdDep, user_service: Annotated[UserService, Depends(get_user_service)]
) -> UserProfileResponse:
    user = await user_service.get_by_id(user_id)
    return UserProfileResponse(
        id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    payload: UpdateUserRequest,
    user_id: CurrentUserIdDep,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfileResponse:
    user = await user_service.update_profile(user_id, payload.full_name)
    return UserProfileResponse(
        id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active
    )
