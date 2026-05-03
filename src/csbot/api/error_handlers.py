from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from csbot.domain.errors import ConfigError, DemoCsBotError, ValidationError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def _handle_validation_error(_request: Request, exc: ValidationError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ConfigError)
    async def _handle_config_error(_request: Request, exc: ConfigError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(DemoCsBotError)
    async def _handle_app_error(_request: Request, exc: DemoCsBotError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})
