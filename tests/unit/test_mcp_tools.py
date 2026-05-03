from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.agents.mcp_tools import build_mcp_tools
from csbot.config.settings import McpConfig


def test_build_mcp_tools_returns_empty_when_disabled() -> None:
    cfg = McpConfig(enabled=False, startup_timeout_sec=10, servers=[])
    assert build_mcp_tools(cfg) == []
