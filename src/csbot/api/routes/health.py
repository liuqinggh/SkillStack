from __future__ import annotations

from fastapi import APIRouter

from csbot.api.deps import RUNTIME_SERVICE_ID, AppContext


def create_health_router(context: AppContext) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": RUNTIME_SERVICE_ID,
            "runtime": "ready",
            "version": context.settings.app.version,
        }

    return router
