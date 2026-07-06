import uuid

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
