import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

from appsec.config import get_settings
from appsec.domain.exceptions import TokenExpiredError, UnauthorizedError

TokenType = Literal["access", "refresh"]


@dataclass(slots=True)
class TokenPayload:
    sub: uuid.UUID
    jti: str
    type: TokenType
    exp: datetime
    org_id: uuid.UUID | None = None


def _encode(
    subject: uuid.UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    org_id: uuid.UUID | None = None,
) -> tuple[str, str]:
    settings = get_settings()
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "jti": jti,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if org_id is not None:
        payload["org_id"] = str(org_id)
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID | None = None) -> tuple[str, str]:
    settings = get_settings()
    return _encode(user_id, "access", timedelta(minutes=settings.jwt_access_token_expire_minutes), org_id)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    settings = get_settings()
    return _encode(user_id, "refresh", timedelta(days=settings.jwt_refresh_token_expire_days))


def decode_token(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        raw = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token") from exc

    org_id = uuid.UUID(raw["org_id"]) if raw.get("org_id") else None
    return TokenPayload(
        sub=uuid.UUID(raw["sub"]),
        jti=raw["jti"],
        type=raw["type"],
        exp=datetime.fromtimestamp(raw["exp"], tz=UTC),
        org_id=org_id,
    )
