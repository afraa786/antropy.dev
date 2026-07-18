class AppException(Exception):
    """Base for all domain/application exceptions."""

    code: str = "app_error"
    status_code: int = 500

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__doc__ or self.code
        super().__init__(self.message)


class NotFoundError(AppException):
    """Requested resource does not exist."""

    code = "not_found"
    status_code = 404


class ConflictError(AppException):
    """Resource already exists or state conflict."""

    code = "conflict"
    status_code = 409


class UnauthorizedError(AppException):
    """Authentication required or credentials invalid."""

    code = "unauthorized"
    status_code = 401


class ForbiddenError(AppException):
    """Authenticated but not permitted."""

    code = "forbidden"
    status_code = 403


class ValidationAppError(AppException):
    """Input failed business validation."""

    code = "validation_error"
    status_code = 422


class DomainNotVerifiedError(AppException):
    """Scan target domain is not verified for ownership."""

    code = "domain_not_verified"
    status_code = 403

    def __init__(self, hostname: str | None = None) -> None:
        message = (
            f"Domain '{hostname}' is not verified. Ownership verification required before "
            "scanning."
            if hostname
            else "Domain is not verified. Ownership verification required before scanning."
        )
        super().__init__(message)


class TokenExpiredError(UnauthorizedError):
    """JWT token has expired."""

    code = "token_expired"


class TokenRevokedError(UnauthorizedError):
    """JWT token has been revoked."""

    code = "token_revoked"


class InvalidCredentialsError(UnauthorizedError):
    """Email or password incorrect."""

    code = "invalid_credentials"
