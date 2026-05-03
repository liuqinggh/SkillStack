from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from csbot.api.deps import AppContext


EXCLUDED_PREFIXES = ('api/', 'ws/')


def create_root_static_router(context: AppContext) -> APIRouter:
    router = APIRouter()
    static_dir = context.settings.project_root / 'static'
    frontend_dist_dir = context.settings.project_root / 'demo-frontend' / 'agent-chat-lite' / 'dist'

    def resolve_index_file() -> tuple[str, str]:
        frontend_index = frontend_dist_dir / 'index.html'
        static_index = static_dir / 'index.html'
        index_file = frontend_index if frontend_index.is_file() else static_index
        if not index_file.is_file():
            raise HTTPException(
                status_code=404,
                detail=f'Frontend index not found: {frontend_index} (fallback: {static_index})',
            )
        return str(index_file), str(frontend_index)

    @router.get('/')
    def index():
        index_file, _ = resolve_index_file()
        return FileResponse(index_file)

    @router.get('/{file_path:path}')
    def static_or_spa(file_path: str):
        if not file_path:
            index_file, _ = resolve_index_file()
            return FileResponse(index_file)
        if file_path.startswith(EXCLUDED_PREFIXES):
            raise HTTPException(status_code=404, detail='Not Found')

        candidate = frontend_dist_dir / file_path
        if candidate.is_file():
            return FileResponse(candidate)

        index_file, frontend_index = resolve_index_file()
        # Only enable SPA fallback when frontend dist exists.
        if index_file == frontend_index:
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail='Not Found')

    return router
