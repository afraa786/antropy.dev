from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from appsec.domain.exceptions import AppException
from appsec.logging import get_logger

logger = get_logger(__name__)


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(exc.code, exc.message)
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500, content=_error_body("internal_error", "Internal server error")
        )
