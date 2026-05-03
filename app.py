"""
FastAPI 启动入口。
挂载路由由 csbot.create_app → create_router 完成（含 /、/health、/api/runtime/sessions、/api/runtime/runs）。
启动方式:
  uvicorn app:app --reload --host 0.0.0.0 --port 8000
  或
  python app.py
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot import create_app
from csbot.config.settings import DEFAULT_DB_PATH, load_settings

DB_PATH = DEFAULT_DB_PATH
app = create_app(DB_PATH)


if __name__ == "__main__":
    import uvicorn
    settings = load_settings(DB_PATH)
    uvicorn.run(
        "app:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
    )
