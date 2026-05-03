"""仅用 root_dir 构造本地 Sandbox 的示例（兼容/示例用）。

正式使用请直接使用 csbot.adapters.sandbox_adapter.LocalSandboxBackend，
并通过 conf.yaml 的 sandbox 配置传入完整 SandboxConfig。
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.adapters.sandbox_adapter import LocalSandboxBackend
from csbot.config.settings import SandboxConfig


class SimpleLocalSandbox(LocalSandboxBackend):
    """仅需 root_dir 的简易包装，其余参数使用默认值。"""

    def __init__(self, root_dir: str):
        cfg = SandboxConfig(
            root_dir=root_dir,
            virtual_mode=True,
            execute_timeout_sec=60,
            max_output_chars=10000,
        )
        super().__init__(cfg)
