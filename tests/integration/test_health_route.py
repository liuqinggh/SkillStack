from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot import create_app
from tests.support.sqlite_config import write_runtime_db


def test_health_route(tmp_path: Path):
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path)
    app = create_app(str(db))
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data.get("runtime") == "ready"
    assert data.get("service") == "demo-csbot-runtime"
