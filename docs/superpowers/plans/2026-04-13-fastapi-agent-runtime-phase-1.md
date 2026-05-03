# FastAPI Agent Runtime Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the demo-oriented `/api/v1/chat` service shape with a FastAPI-hosted Agent Runtime Phase 1 that exposes `session/run/event` semantics over HTTP + SSE while using LiteLLM, DeepAgents, and LangGraph behind stable internal boundaries.

**Architecture:** Introduce new `providers`, `agents`, `runtime`, `sessions`, and `api/routes` units without rewriting everything in one pass. Build the new runtime path first, validate it with focused tests, then switch the app factory to the new routes and delete the old chat entrypoints once the new API and SSE flow are stable.

**Tech Stack:** Python 3.11+, FastAPI, deepagents, langgraph, LiteLLM, pytest

---

### Task 1: Add LiteLLM-backed provider layer

**Files:**
- Create: `src/csbot/providers/__init__.py`
- Create: `src/csbot/providers/base.py`
- Create: `src/csbot/providers/litellm_provider.py`
- Modify: `src/csbot/config/settings.py`
- Test: `tests/unit/test_litellm_provider.py`

- [ ] **Step 1: Write the failing provider test**

```python
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.providers.litellm_provider import LiteLLMProvider


def test_litellm_provider_builds_chat_openai_kwargs():
    provider = LiteLLMProvider(
        model="claude-3-7-sonnet",
        api_base="http://127.0.0.1:4000",
        api_key="sk-local",
        temperature=0.2,
        timeout_sec=30,
        max_tokens=2048,
    )

    kwargs = provider.build_chat_openai_kwargs()

    assert kwargs["model"] == "claude-3-7-sonnet"
    assert kwargs["base_url"] == "http://127.0.0.1:4000"
    assert kwargs["api_key"] == "sk-local"
    assert kwargs["temperature"] == 0.2
    assert kwargs["timeout"] == 30
    assert kwargs["max_tokens"] == 2048
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_litellm_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'csbot.providers'`

- [ ] **Step 3: Add provider configuration and implementation**

`src/csbot/providers/base.py`

```python
from __future__ import annotations

from typing import Protocol


class ModelProvider(Protocol):
    def build_chat_openai_kwargs(self) -> dict:
        pass
```

`src/csbot/providers/litellm_provider.py`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LiteLLMProvider:
    model: str
    api_base: str
    api_key: str
    temperature: float
    timeout_sec: int
    max_tokens: int

    def build_chat_openai_kwargs(self) -> dict:
        return {
            "model": self.model,
            "base_url": self.api_base,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "timeout": self.timeout_sec,
            "max_tokens": self.max_tokens,
        }
```

`src/csbot/providers/__init__.py`

```python
from csbot.providers.base import ModelProvider
from csbot.providers.litellm_provider import LiteLLMProvider

__all__ = ["ModelProvider", "LiteLLMProvider"]
```

`src/csbot/config/settings.py`

```python
@dataclass(frozen=True)
class LlmConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    temperature: float
    timeout_sec: int
    max_tokens: int


if llm.provider.strip().lower() != "litellm":
    raise ConfigError("llm.provider must be 'litellm' for runtime phase 1")
```

- [ ] **Step 4: Run the provider test to verify it passes**

Run: `pytest tests/unit/test_litellm_provider.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_litellm_provider.py src/csbot/providers/__init__.py src/csbot/providers/base.py src/csbot/providers/litellm_provider.py src/csbot/config/settings.py
git commit -m "feat: add litellm provider layer"
```

### Task 2: Introduce runtime events and session/run schemas

**Files:**
- Create: `src/csbot/runtime/__init__.py`
- Create: `src/csbot/runtime/events.py`
- Create: `src/csbot/api/schemas/common.py`
- Create: `src/csbot/api/schemas/session.py`
- Create: `src/csbot/api/schemas/run.py`
- Create: `tests/unit/test_runtime_events.py`

- [ ] **Step 1: Write the failing event normalization test**

```python
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.runtime.events import RuntimeEvent, RuntimeEventType


def test_runtime_event_dump_excludes_none_fields():
    event = RuntimeEvent(
        type=RuntimeEventType.DELTA,
        run_id="run_123",
        session_id="sess_123",
        delta="你",
    )

    payload = event.model_dump(exclude_none=True)

    assert payload == {
        "type": "delta",
        "run_id": "run_123",
        "session_id": "sess_123",
        "delta": "你",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_runtime_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'csbot.runtime'`

- [ ] **Step 3: Add runtime event and public schema models**

`src/csbot/runtime/events.py`

```python
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class RuntimeEventType(str, Enum):
    STARTED = "started"
    PLANNING = "planning"
    DELTA = "delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"


class RuntimeEvent(BaseModel):
    type: RuntimeEventType
    run_id: str
    session_id: str
    delta: str | None = None
    message: str | None = None
    output_text: str | None = None
    error: str | None = None
```

`src/csbot/api/schemas/common.py`

```python
from pydantic import BaseModel


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    run_id: str | None = None
    session_id: str | None = None
    retryable: bool = False
    details: dict | None = None
```

`src/csbot/api/schemas/session.py`

```python
from pydantic import BaseModel


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str = "ready"
```

`src/csbot/api/schemas/run.py`

```python
from pydantic import BaseModel, Field


class RunInput(BaseModel):
    message: str = Field(min_length=1)


class AgentSpec(BaseModel):
    id: str = "general-assistant"
    mode: str = "chat"


class ModelSpec(BaseModel):
    provider: str = "litellm"
    model: str


class RunRequest(BaseModel):
    input: RunInput
    agent: AgentSpec
    model: ModelSpec
    session_id: str | None = None
    stream: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)
```

`src/csbot/runtime/__init__.py`

```python
from csbot.runtime.events import RuntimeEvent, RuntimeEventType

__all__ = ["RuntimeEvent", "RuntimeEventType"]
```

- [ ] **Step 4: Run the event test to verify it passes**

Run: `pytest tests/unit/test_runtime_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_runtime_events.py src/csbot/runtime/__init__.py src/csbot/runtime/events.py src/csbot/api/schemas/common.py src/csbot/api/schemas/session.py src/csbot/api/schemas/run.py
git commit -m "feat: add runtime event and api schemas"
```

### Task 3: Add DeepAgents runtime wrapper and runtime service

**Files:**
- Create: `src/csbot/agents/__init__.py`
- Create: `src/csbot/agents/deepagents_runtime.py`
- Create: `src/csbot/runtime/context.py`
- Create: `src/csbot/runtime/lifecycle.py`
- Create: `src/csbot/runtime/service.py`
- Create: `tests/unit/test_runtime_service.py`
- Modify: `src/csbot/adapters/deep_agent_adapter.py`
- Modify: `src/csbot/providers/litellm_provider.py`

- [ ] **Step 1: Write the failing runtime service test**

```python
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.runtime.service import RuntimeService


class FakeAgentRuntime:
    def run_stream(self, message: str, session_id: str):
        yield "你"
        yield "好"


def test_runtime_service_emits_started_delta_done():
    svc = RuntimeService(agent_runtime=FakeAgentRuntime())

    events = list(
        svc.run_stream(
            message="hello",
            session_id="sess_1",
            run_id="run_1",
        )
    )

    assert [event.type for event in events] == ["started", "delta", "delta", "done"]
    assert events[-1].output_text == "你好"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_runtime_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'csbot.runtime.service'`

- [ ] **Step 3: Implement runtime wrapper and lifecycle service**

`src/csbot/agents/deepagents_runtime.py`

```python
from __future__ import annotations

from collections.abc import Iterator

from csbot.adapters.deep_agent_adapter import DeepAgentAdapter
from csbot.providers import LiteLLMProvider


class DeepAgentsRuntime:
    def __init__(self, settings, provider: LiteLLMProvider):
        self._adapter = DeepAgentAdapter(settings=settings, llm=provider.build_chat_model())

    def run_once(self, message: str, session_id: str) -> str:
        return self._adapter.run_turn(message, session_id)

    def run_stream(self, message: str, session_id: str) -> Iterator[str]:
        yield from self._adapter.run_stream(message, session_id)
```

`src/csbot/runtime/context.py`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunContext:
    run_id: str
    session_id: str
    message: str
```

`src/csbot/runtime/lifecycle.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class RunLifecycle:
    run_id: str
    session_id: str
    status: str = "queued"
    started_at: float = field(default_factory=time)
    finished_at: float | None = None
    error: str | None = None
```

`src/csbot/runtime/service.py`

```python
from __future__ import annotations

from collections.abc import Iterator

from csbot.runtime.context import RunContext
from csbot.runtime.events import RuntimeEvent, RuntimeEventType


class RuntimeService:
    def __init__(self, agent_runtime):
        self._agent_runtime = agent_runtime

    def run_stream(self, message: str, session_id: str, run_id: str) -> Iterator[RuntimeEvent]:
        ctx = RunContext(run_id=run_id, session_id=session_id, message=message)
        yield RuntimeEvent(type=RuntimeEventType.STARTED, run_id=ctx.run_id, session_id=ctx.session_id)

        full = ""
        for delta in self._agent_runtime.run_stream(message, session_id):
            full += delta
            yield RuntimeEvent(
                type=RuntimeEventType.DELTA,
                run_id=ctx.run_id,
                session_id=ctx.session_id,
                delta=delta,
            )

        yield RuntimeEvent(
            type=RuntimeEventType.DONE,
            run_id=ctx.run_id,
            session_id=ctx.session_id,
            output_text=full,
        )
```

`src/csbot/agents/__init__.py`

```python
from csbot.agents.deepagents_runtime import DeepAgentsRuntime

__all__ = ["DeepAgentsRuntime"]
```

`src/csbot/adapters/deep_agent_adapter.py`

```python
from langchain_openai import ChatOpenAI


class DeepAgentAdapter:
    def __init__(self, settings: Settings, llm: ChatOpenAI):
        self._settings = settings
        self._llm = llm
        self._chatbot = create_deep_agent(
            model=self._llm,
            system_prompt=settings.agent.system_prompt,
            skills=settings.agent.skills_sources,
            backend=backend_factory,
            memory=settings.agent.memory_files,
            checkpointer=MemorySaver(),
        )
```

`src/csbot/providers/litellm_provider.py`

```python
from langchain_openai import ChatOpenAI


@dataclass(frozen=True)
class LiteLLMProvider:
    model: str
    api_base: str
    api_key: str
    temperature: float
    timeout_sec: int
    max_tokens: int

    def build_chat_openai_kwargs(self) -> dict:
        return {
            "model": self.model,
            "base_url": self.api_base,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "timeout": self.timeout_sec,
            "max_tokens": self.max_tokens,
        }

    def build_chat_model(self) -> ChatOpenAI:
        return ChatOpenAI(**self.build_chat_openai_kwargs())
```

- [ ] **Step 4: Run the runtime service test to verify it passes**

Run: `pytest tests/unit/test_runtime_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_runtime_service.py src/csbot/agents/__init__.py src/csbot/agents/deepagents_runtime.py src/csbot/runtime/context.py src/csbot/runtime/lifecycle.py src/csbot/runtime/service.py src/csbot/adapters/deep_agent_adapter.py src/csbot/providers/litellm_provider.py
git commit -m "feat: add runtime service over deepagents"
```

### Task 4: Add session service, repository, and AppContext wiring for runtime mode

**Files:**
- Create: `src/csbot/sessions/__init__.py`
- Create: `src/csbot/sessions/repository.py`
- Create: `src/csbot/sessions/service.py`
- Modify: `src/csbot/api/deps.py`
- Modify: `src/csbot/config/settings.py`
- Create: `tests/unit/test_sessions_service.py`

- [ ] **Step 1: Write the failing session service test**

```python
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.sessions.service import SessionsService


def test_sessions_service_creates_predictable_session_ids():
    svc = SessionsService()

    session = svc.create()

    assert session.session_id.startswith("sess_")
    assert session.status == "ready"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_sessions_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'csbot.sessions'`

- [ ] **Step 3: Add session repository and dependency wiring**

`src/csbot/sessions/repository.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionRecord:
    session_id: str
    status: str = "ready"
    run_ids: list[str] = field(default_factory=list)


class InMemorySessionRepository:
    def __init__(self):
        self._items: dict[str, SessionRecord] = {}

    def save(self, record: SessionRecord) -> SessionRecord:
        self._items[record.session_id] = record
        return record

    def get(self, session_id: str) -> SessionRecord | None:
        return self._items.get(session_id)
```

`src/csbot/sessions/service.py`

```python
from __future__ import annotations

from uuid import uuid4

from csbot.sessions.repository import InMemorySessionRepository, SessionRecord


class SessionsService:
    def __init__(self, repository: InMemorySessionRepository | None = None):
        self._repository = repository or InMemorySessionRepository()

    def create(self) -> SessionRecord:
        record = SessionRecord(session_id=f"sess_{uuid4().hex[:12]}")
        return self._repository.save(record)

    def get(self, session_id: str) -> SessionRecord | None:
        return self._repository.get(session_id)
```

`src/csbot/sessions/__init__.py`

```python
from csbot.sessions.repository import InMemorySessionRepository, SessionRecord
from csbot.sessions.service import SessionsService

__all__ = ["InMemorySessionRepository", "SessionRecord", "SessionsService"]
```

`src/csbot/api/deps.py`

```python
from csbot.agents import DeepAgentsRuntime
from csbot.providers import LiteLLMProvider
from csbot.runtime.service import RuntimeService
from csbot.sessions import InMemorySessionRepository, SessionsService


@dataclass(frozen=True)
class AppContext:
    settings: Settings
    provider: LiteLLMProvider
    runtime_service: RuntimeService
    sessions_service: SessionsService
    executor: ThreadPoolExecutor
```

`src/csbot/config/settings.py`

```python
@dataclass(frozen=True)
class ApiConfig:
    cors_allow_origins: list[str]
    max_request_chars: int
    chat_timeout_sec: int
    runtime_prefix: str


api = ApiConfig(
    cors_allow_origins=_as_list(_required(api_raw, "cors_allow_origins", "api"), "api.cors_allow_origins"),
    max_request_chars=int(_required(api_raw, "max_request_chars", "api")),
    chat_timeout_sec=int(api_raw.get("chat_timeout_sec", 120)),
    runtime_prefix=str(api_raw.get("runtime_prefix", "/api/runtime")),
)
```

- [ ] **Step 4: Run the session service test to verify it passes**

Run: `pytest tests/unit/test_sessions_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_sessions_service.py src/csbot/sessions/__init__.py src/csbot/sessions/repository.py src/csbot/sessions/service.py src/csbot/api/deps.py src/csbot/config/settings.py
git commit -m "feat: add runtime session service wiring"
```

### Task 5: Add runtime HTTP routes and SSE endpoint

**Files:**
- Create: `src/csbot/api/routes/runs.py`
- Create: `src/csbot/api/routes/sessions.py`
- Create: `src/csbot/api/routes/health.py`
- Create: `src/csbot/api/routes/__init__.py`
- Create: `src/csbot/api/sse.py`
- Modify: `src/csbot/app_factory.py`
- Modify: `app.py`
- Create: `tests/integration/test_runtime_routes.py`

- [ ] **Step 1: Write the failing integration test**

```python
from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot import create_app


def test_create_session_and_stream_run():
    app = create_app(str(PROJECT_ROOT / "conf.yaml"))
    client = TestClient(app)

    session_resp = client.post("/api/runtime/sessions")
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    with client.stream(
        "POST",
        f"/api/runtime/sessions/{session_id}/runs",
        json={
            "input": {"message": "hello"},
            "agent": {"id": "general-assistant", "mode": "chat"},
            "model": {"provider": "litellm", "model": "claude-3-7-sonnet"},
            "stream": True,
        },
    ) as resp:
        body = "".join(resp.iter_text())

    assert resp.status_code == 200
    assert '"type": "started"' in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_runtime_routes.py -v`
Expected: FAIL with `404 != 200` for `/api/runtime/sessions`

- [ ] **Step 3: Implement route modules and SSE helper**

`src/csbot/api/sse.py`

```python
from __future__ import annotations

import json


def sse_data(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
```

`src/csbot/api/routes/health.py`

```python
from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "demo-csbot-runtime"}
```

`src/csbot/api/routes/sessions.py`

```python
from fastapi import APIRouter

from csbot.api.schemas.session import CreateSessionResponse


def build_sessions_router(context) -> APIRouter:
    router = APIRouter(prefix="/api/runtime/sessions", tags=["sessions"])

    @router.post("", response_model=CreateSessionResponse)
    def create_session():
        record = context.sessions_service.create()
        return CreateSessionResponse(session_id=record.session_id)

    return router
```

`src/csbot/api/routes/runs.py`

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from csbot.api.schemas.run import RunRequest
from csbot.api.sse import sse_data


def build_runs_router(context) -> APIRouter:
    router = APIRouter(tags=["runs"])

    @router.post("/api/runtime/sessions/{session_id}/runs")
    def create_session_run(session_id: str, req: RunRequest):
        run_id = f"run_{session_id}"

        if not req.stream:
            events = list(context.runtime_service.run_stream(req.input.message, session_id, run_id))
            return {"run_id": run_id, "session_id": session_id, "status": "succeeded", "output_text": events[-1].output_text}

        def event_generator():
            for event in context.runtime_service.run_stream(req.input.message, session_id, run_id):
                yield sse_data(event.model_dump(exclude_none=True))

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return router
```

`src/csbot/api/routes/__init__.py`

```python
from fastapi import APIRouter

from csbot.api.routes.health import router as health_router
from csbot.api.routes.runs import build_runs_router
from csbot.api.routes.sessions import build_sessions_router


def build_api_router(context) -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(build_sessions_router(context))
    router.include_router(build_runs_router(context))
    return router
```

`src/csbot/app_factory.py`

```python
from csbot.api.routes import build_api_router


app.include_router(build_api_router(context))
```

`app.py`

```python
"""FastAPI runtime entrypoint."""

from csbot import create_app

app = create_app("conf.yaml")
```

- [ ] **Step 4: Run the integration test to verify it passes**

Run: `pytest tests/integration/test_runtime_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_runtime_routes.py src/csbot/api/sse.py src/csbot/api/routes/__init__.py src/csbot/api/routes/health.py src/csbot/api/routes/sessions.py src/csbot/api/routes/runs.py src/csbot/app_factory.py app.py
git commit -m "feat: expose runtime sessions and runs api"
```

### Task 6: Remove legacy chat-service path and stabilize runtime checks

**Files:**
- Modify: `src/csbot/api/deps.py`
- Delete: `src/csbot/api/routes.py`
- Delete: `src/csbot/services/chat_service.py`
- Delete: `src/csbot/services/stream_service.py`
- Modify: `tests/integration/test_health_route.py`
- Create: `tests/integration/test_runtime_health_route.py`
- Create: `tests/unit/test_runtime_errors.py`
- Modify: `docs/设计文档.md`

- [ ] **Step 1: Write the failing runtime health and error tests**

```python
from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot import create_app


def test_runtime_health_route_service_name():
    app = create_app(str(PROJECT_ROOT / "conf.yaml"))
    client = TestClient(app)

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["service"] == "demo-csbot-runtime"
```

```python
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.runtime.events import RuntimeEventType


def test_runtime_event_type_has_error():
    assert RuntimeEventType.ERROR.value == "error"
```

- [ ] **Step 2: Run tests to verify they fail if legacy wiring remains**

Run: `pytest tests/integration/test_runtime_health_route.py tests/unit/test_runtime_errors.py -v`
Expected: FAIL because runtime health response and runtime modules are not yet the only active path

- [ ] **Step 3: Remove legacy route wiring and update docs**

`src/csbot/api/deps.py`

```python
@dataclass(frozen=True)
class AppContext:
    settings: Settings
    provider: LiteLLMProvider
    runtime_service: RuntimeService
    sessions_service: SessionsService
    executor: ThreadPoolExecutor


def build_context(conf_path: str = "conf.yaml") -> AppContext:
    settings = load_settings(conf_path)
    provider = LiteLLMProvider(
        model=settings.llm.model,
        api_base=settings.llm.base_url,
        api_key=settings.llm.api_key,
        temperature=settings.llm.temperature,
        timeout_sec=settings.llm.timeout_sec,
        max_tokens=settings.llm.max_tokens,
    )
    session_repository = InMemorySessionRepository()
    sessions_service = SessionsService(session_repository)
    agent_runtime = DeepAgentsRuntime(settings=settings, provider=provider)
    runtime_service = RuntimeService(agent_runtime=agent_runtime)
    executor = ThreadPoolExecutor(max_workers=settings.agent.thread_pool_workers)
    return AppContext(
        settings=settings,
        provider=provider,
        runtime_service=runtime_service,
        sessions_service=sessions_service,
        executor=executor,
    )
```

`docs/设计文档.md`

```markdown
## 一、项目概述

**demo-csbot** 已切换为基于 **FastAPI Runtime API** 的 Agent Runtime Demo，对外通过 `session/run/event` 协议提供 HTTP 与 SSE 能力。
```

- [ ] **Step 4: Run focused regression tests**

Run: `pytest tests/unit/test_litellm_provider.py tests/unit/test_runtime_events.py tests/unit/test_runtime_service.py tests/unit/test_sessions_service.py tests/unit/test_runtime_errors.py tests/integration/test_runtime_routes.py tests/integration/test_runtime_health_route.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/csbot/api/deps.py src/csbot/api/routes.py src/csbot/services/chat_service.py src/csbot/services/stream_service.py tests/integration/test_health_route.py tests/integration/test_runtime_health_route.py tests/unit/test_runtime_errors.py docs/设计文档.md
git commit -m "refactor: remove legacy chat runtime path"
```
