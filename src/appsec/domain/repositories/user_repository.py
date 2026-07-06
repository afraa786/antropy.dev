import uuid
from typing import Protocol

from appsec.domain.entities.user import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def create(self, user: User) -> User: ...

    async def update(self, user: User) -> User: ...
