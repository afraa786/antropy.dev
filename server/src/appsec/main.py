from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from appsec.api.error_handlers import register_error_handlers
from appsec.api.middleware import RequestContextMiddleware
from appsec.api.v1.router import api_router
from appsec.config import get_settings
from appsec.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "AI-powered Application Security SaaS backend. "
            "Scans are only permitted against domains with verified ownership."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
