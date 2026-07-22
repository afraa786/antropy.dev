import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from appsec.domain.entities.user import User
from appsec.domain.exceptions import NotFoundError
from appsec.domain.repositories.user_repository import UserRepository
from appsec.infrastructure.security.password import hash_password


class UserService:
    def __init__(self, session: AsyncSession, user_repository: UserRepository) -> None:
        self._session = session
        self._users = user_repository

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def update_profile(self, user_id: uuid.UUID, full_name: str | None) -> User:
        user = await self.get_by_id(user_id)
        user.full_name = full_name
        updated = await self._users.update(user)
        await self._session.commit()
        return updated

    async def create_anonymous(self) -> User:
        """Create a temporary anonymous user for demo/quick-scan flows."""
        user = User(
            id=uuid.uuid4(),
            email=f"anon-{uuid.uuid4().hex[:8]}@demo.local",
            hashed_password=hash_password("demo-" + uuid.uuid4().hex[:16]),
            is_active=True,
            full_name="Demo User",
        )
        created = await self._users.create(user)
        await self._session.commit()
        return created
