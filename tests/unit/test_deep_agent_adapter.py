from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.adapters.deep_agent_adapter import DeepAgentAdapter
from csbot.config.settings import load_settings
from tests.support.sqlite_config import write_runtime_db


def test_reset_runtime_cache_rebuilds_agent_runtime(tmp_path: Path, monkeypatch) -> None:
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path)
    settings = load_settings(str(db))
    created: list[str] = []

    class _FakeRuntime:
        def __init__(self, _settings, _provider, *, profile, agent_id: str) -> None:
            created.append(agent_id)
            self.agent_id = agent_id

        def run_turn(self, user_input: str, session_id: str) -> str:
            return f"{self.agent_id}:{session_id}:{user_input}"

        def iter_stream_deltas(self, user_input: str, session_id: str):
            yield self.run_turn(user_input, session_id)

    monkeypatch.setattr("csbot.adapters.deep_agent_adapter.DeepAgentsRuntime", _FakeRuntime)
    adapter = DeepAgentAdapter(settings)

    first = adapter.run_turn("hi", "s1", agent_id="default")
    second = adapter.run_turn("hi", "s2", agent_id="default")
    assert first == "default:s1:hi"
    assert second == "default:s2:hi"
    assert created == ["default"]

    adapter.reset_runtime_cache()
    third = adapter.run_turn("hi", "s3", agent_id="default")
    assert third == "default:s3:hi"
    assert created == ["default", "default"]
