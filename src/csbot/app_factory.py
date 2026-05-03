from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from csbot.api.deps import AppContext, get_context
from csbot.config.settings import DEFAULT_DB_PATH
from csbot.api.error_handlers import register_error_handlers
from csbot.api.routes import create_router
from csbot.logging_config import configure_logging


def create_app(db_path: str = DEFAULT_DB_PATH, *, app_context: AppContext | None = None) -> FastAPI:
    context = app_context if app_context is not None else get_context(db_path)
    configure_logging(context.settings)

    app = FastAPI(
        title=context.settings.app.name,
        description="Deep Agent Chatbot 对外 HTTP 接口",
        version=context.settings.app.version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=context.settings.api.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    app.include_router(create_router(context))
    register_error_handlers(app)
    return app
