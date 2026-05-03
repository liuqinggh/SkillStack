from __future__ import annotations

import subprocess
from pathlib import Path

from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol

from csbot.config.settings import SandboxConfig


class LocalSandboxBackend(FilesystemBackend, SandboxBackendProtocol):
    def __init__(self, config: SandboxConfig):
        root = Path(config.root_dir).resolve()
        super().__init__(root_dir=root, virtual_mode=config.virtual_mode)
        self._sandbox_root = root
        self._timeout_sec = config.execute_timeout_sec
        self._max_output_chars = config.max_output_chars
        self._id = "local-sandbox-backend"

    @property
    def id(self) -> str:
        return self._id

    def execute(self, command: str) -> ExecuteResponse:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self._sandbox_root,
                capture_output=True,
                text=True,
                timeout=self._timeout_sec,
            )
            output = result.stdout + result.stderr
            truncated = len(output) > self._max_output_chars
            if truncated:
                output = output[: self._max_output_chars] + "\n... (truncated)"

            return ExecuteResponse(
                output=output,
                exit_code=result.returncode,
                truncated=truncated,
            )
        except Exception as e:
            return ExecuteResponse(
                output=str(e),
                exit_code=1,
                truncated=False,
            )
