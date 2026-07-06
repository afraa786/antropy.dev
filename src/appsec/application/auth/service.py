import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from appsec.config import get_settings
from appsec.domain.entities.user import User
from appsec.domain.exceptions import ConflictError, InvalidCredentialsError, UnauthorizedError
from appsec.domain.repositories.user_repository import UserRepository
from appsec.infrastructure.db.models.refresh_token import RefreshTokenModel
from appsec.infrastructure.security.jwt import create_access_token, create_refresh_token, decode_token
from appsec.infrastructure.security.password import hash_password, verify_password
from appsec.infrastructure.security.redis_blacklist import TokenBlacklist
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        token_blacklist: TokenBlacklist,
    ) -> None:
        self._session = session
        self._users = user_repository
        self._blacklist = token_blacklist

    async def register(self, email: str, password: str, full_name: str | None) -> User:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError(f"User with email '{email}' already exists")

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(UTC),
        )
        created = await self._users.create(user)
        await self._session.commit()
        return created

    async def login(self, email: str, password: str) -> tuple[str, str]:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise UnauthorizedError("User account is disabled")

        return await self._issue_token_pair(user.id)

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        payload = decode_token(refresh_token)
        if payload.type != "refresh":
            raise UnauthorizedError("Invalid token type")
        if await self._blacklist.is_revoked(payload.jti):
            raise UnauthorizedError("Token has been revoked")

        token_hash = _hash_token(refresh_token)
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored is None or stored.revoked_at is not None:
            raise UnauthorizedError("Refresh token not recognized")

        stored.revoked_at = datetime.now(UTC)
        await self._blacklist.revoke(payload.jti, payload.exp)

        new_access, new_refresh = await self._issue_token_pair(payload.sub)
        await self._session.commit()
        return new_access, new_refresh

    async def logout(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        token_hash = _hash_token(refresh_token)
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)
            await self._blacklist.revoke(payload.jti, payload.exp)
            await self._session.commit()

    async def _issue_token_pair(self, user_id: uuid.UUID) -> tuple[str, str]:
        settings = get_settings()
        access_token, _ = create_access_token(user_id)
        refresh_token, _ = create_refresh_token(user_id)

        refresh_model = RefreshTokenModel(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days),
        )
        self._session.add(refresh_model)
        await self._session.flush()
        return access_token, refresh_token
