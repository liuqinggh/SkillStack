# FastAPI Agent Runtime Design

## 1. Background

`demo-csbot` already has a usable backend skeleton built with `FastAPI + deepagents + LangGraph + SSE`, but its current shape is still a demo-oriented chat service:

- the public API is centered on `/api/v1/chat` instead of a reusable runtime object model
- `deep_agent_adapter.py` currently mixes model construction, agent bootstrap, stream parsing, and session semantics
- the frontend contract is coupled to chat reply behavior rather than a general agent execution lifecycle

The target of this design is to evolve the project into a standalone FastAPI-based Agent Runtime Service. Future Umi Max frontend work should treat it as an intelligent execution backend rather than as a simple chat endpoint.

## 2. Goal

Build a minimum viable backend runtime with these properties:

- FastAPI is the primary and independent backend host
- the public API is centered on `session`, `run`, and `event`
- LiteLLM is the unified model access layer
- DeepAgents is responsible for planning, skills, and subagent execution
- LangGraph is responsible for runtime state and checkpoint semantics
- SSE is the first-class streaming transport for the minimum viable release

## 3. Non-Goals For Phase 1

The first phase intentionally does **not** include:

- WebSocket as a required transport
- multi-tenant isolation
- admin console or visual operations dashboard
- distributed queue workers
- a public skill marketplace UI
- long-term coexistence with the old `/api/v1/chat` interface

## 4. Design Decision

The selected direction is:

**FastAPI independent backend + standard runtime architecture**

This means:

- the backend is not designed around a single chat endpoint
- the runtime protocol is modeled explicitly
- internal responsibilities are separated by capability instead of being collapsed into one adapter
- future frontend or CLI clients depend on runtime contracts, not on DeepAgents or LangGraph internals

## 5. Architecture Overview

### 5.1 Top-Level Layers

The runtime is organized into the following layers:

1. `api`
   - exposes HTTP, SSE, and later WebSocket endpoints
   - validates requests and maps runtime objects to transport responses

2. `api.schemas`
   - defines transport-safe request and response models
   - standardizes `RunRequest`, `RunSummary`, `RunEvent`, `SessionSummary`, and `ErrorEnvelope`

3. `runtime`
   - provides the unified execution entrypoints such as `run_once`, `run_stream`, `cancel_run`
   - assembles model provider, agent runtime, graph state, and session context
   - normalizes internal execution updates into stable runtime events

4. `providers`
   - encapsulates LiteLLM access
   - handles model routing, model parameters, timeout, fallback, and retry rules

5. `agents`
   - encapsulates DeepAgents harness construction and agent execution semantics
   - owns planning, skill loading, tool execution, and subagent spawning behavior

6. `graphs`
   - encapsulates LangGraph state machine and checkpoint behavior
   - maps runtime sessions to graph threads/checkpoints

7. `sessions`
   - manages session identity, session persistence, and session-to-graph mapping

8. `observability`
   - records `run_id`, timestamps, structured logs, tool traces, and error attribution

### 5.2 Boundary Rules

Each layer has a single clear responsibility:

- `providers` decides **how a model is called**
- `agents` decides **how an agent thinks and acts**
- `graphs` decides **how state is persisted and resumed**
- `runtime` decides **how an execution is assembled, driven, and exposed**
- `api` decides **how clients communicate with the runtime**

This separation is important because the current project already shows the downside of a mixed-responsibility adapter. Once planning, skills, session state, and model routing all evolve at the same time, a monolithic adapter becomes a bug farm with good intentions.

## 6. Runtime Object Model

### 6.1 Session

`Session` represents a durable conversational or task context.

Responsibilities:

- own the public `session_id`
- map `session_id` to the underlying LangGraph thread/checkpoint identity
- store context summary and recent runs
- provide a stable unit for resume and inspection

External clients should use `session_id`. Internal graph code may still use a thread identity, but that must remain an implementation detail.

### 6.2 Run

`Run` represents one concrete agent execution attempt inside or outside a session.

Responsibilities:

- capture input payload and normalized configuration
- capture selected agent, model configuration, metadata, and session reference
- record status transitions and final output
- store timing, error, and event summary information

Recommended statuses:

- `queued`
- `running`
- `planning`
- `acting`
- `streaming`
- `succeeded`
- `failed`
- `cancelled`

### 6.3 Event

`Event` represents a streamable unit in the execution lifecycle.

Phase 1 runtime event types should include:

- `started`
- `planning`
- `delta`
- `tool_call`
- `tool_result`
- `done`
- `error`

The runtime must normalize internal framework chunks into these event types. Frontends must never depend directly on raw DeepAgents or LangGraph event shapes.

## 7. Public API Design

### 7.1 Recommended Endpoints

Phase 1 public endpoints:

- `POST /api/runtime/sessions`
  - create a new session and return `session_id`

- `GET /api/runtime/sessions/{session_id}`
  - return session summary, latest run references, and lightweight context metadata

- `POST /api/runtime/sessions/{session_id}/runs`
  - create and execute a new run bound to an existing session

- `POST /api/runtime/runs`
  - create and execute a new run without requiring a pre-created session

- `GET /api/runtime/runs/{run_id}`
  - return run state, error, timing, and final output summary

- `POST /api/runtime/runs/{run_id}/cancel`
  - cancel an in-progress run when supported by the execution path

### 7.2 Request Shape

The request model should be centered on runtime execution instead of a raw chat message:

```json
{
  "input": {
    "message": "帮我分析这段日志"
  },
  "agent": {
    "id": "general-assistant",
    "mode": "chat"
  },
  "model": {
    "provider": "litellm",
    "model": "claude-3-7-sonnet"
  },
  "session_id": "sess_xxx",
  "stream": true,
  "metadata": {
    "source": "web"
  }
}
```

This shape leaves room for future non-chat inputs while still serving the current chat-style use case.

### 7.3 Streaming Transport

Phase 1 uses **SSE as the primary streaming transport**.

Reasons:

- the minimum viable product needs one-way streaming, not a full duplex control channel
- SSE maps naturally to token-like or event-like model output
- frontend integration is simpler
- debugging and proxy compatibility are easier than WebSocket in the early phase

WebSocket remains a reserved extension point for future requirements such as:

- bidirectional runtime control
- collaborative sessions
- live operator consoles
- interactive run interruption and resume workflows

## 8. Internal Responsibilities

### 8.1 Providers Layer

The `providers` layer exposes a stable internal interface such as:

- `create_client()`
- `run_completion()`
- `run_stream()`

Responsibilities:

- wrap LiteLLM access
- resolve base URL, API key, model name, and generation parameters
- centralize provider-level timeout and fallback rules
- avoid leaking provider-specific details into agent or API code

### 8.2 Agents Layer

The `agents` layer exposes a stable interface such as:

- `build_agent_runtime()`
- `run_agent_once()`
- `run_agent_stream()`

Responsibilities:

- bootstrap DeepAgents with planning, skill loading, memory, and subagent behavior
- integrate tool and skill configuration
- present framework output in a runtime-friendly intermediate shape

This layer must not know about HTTP requests, SSE formatting, or frontend response contracts.

### 8.3 Graphs Layer

The `graphs` layer exposes a stable interface such as:

- `resolve_thread(session_id)`
- `load_checkpoint(session_id)`
- `persist_checkpoint(session_id, state)`

Responsibilities:

- own LangGraph checkpoint handling
- separate graph state restoration from API or provider logic
- ensure session recovery and future resume semantics are not hard-coded inside routes

### 8.4 Runtime Layer

The `runtime` layer is the system orchestrator.

Responsibilities:

- generate `run_id`
- resolve or create session context
- assemble provider, agent runtime, and graph state
- drive synchronous or streaming execution
- normalize emitted events
- persist lifecycle data for later inspection

The runtime layer is the only layer allowed to know the full lifecycle of a run.

## 9. Error Handling

The runtime must return structured and attributable errors.

Error categories:

- `validation_error`
- `provider_error`
- `agent_error`
- `graph_error`
- `storage_error`
- `runtime_error`

Each error envelope should include:

- `code`
- `message`
- `run_id` when available
- `session_id` when available
- `retryable` boolean
- optional `details`

Streaming errors should be emitted as runtime `error` events before the stream closes.

## 10. Observability

Every run should produce:

- a unique `run_id`
- start and end timestamps
- duration
- status transitions
- selected model and agent identifiers
- tool execution trace summary
- failure source attribution

Phase 1 does not need a full tracing platform, but it does need enough structured logs to answer:

- which run failed
- at what stage it failed
- whether the failure came from provider, agent logic, graph state, or storage

## 11. Recommended Directory Structure

```text
src/csbot/
  api/
    routes/
      runs.py
      sessions.py
      health.py
    schemas/
      run.py
      session.py
      common.py
    sse.py
    errors.py
  runtime/
    service.py
    events.py
    lifecycle.py
    context.py
  providers/
    litellm_provider.py
    base.py
  agents/
    deepagents_runtime.py
    skill_registry.py
    prompt_loader.py
  graphs/
    session_graph.py
    checkpoint_store.py
  sessions/
    service.py
    repository.py
  observability/
    logging.py
    tracing.py
  config/
  domain/
  storage/
```

This structure keeps runtime semantics explicit and prevents the current `adapter-heavy` organization from becoming the permanent architecture.

## 12. Migration Plan

The project should migrate incrementally, not via a blind rewrite.

### Step 1

Introduce foundational `providers` and `runtime` modules and make a new `run_stream()` path work through LiteLLM + DeepAgents.

### Step 2

Add new `sessions` and `runs` routes with `session_id` and `run_id` contracts. Keep old code only as short-term migration scaffolding.

### Step 3

Split current `deep_agent_adapter` responsibilities across:

- `providers`
- `agents`
- `runtime` event normalization

### Step 4

Add run inspection, structured error envelopes, session repository behavior, and stable SSE event semantics.

### Step 5

Remove the old `/api/v1/chat` path and demo-oriented static page once the new runtime API is verified.

Long-term dual-track support is explicitly discouraged. The user already approved breaking compatibility, so the migration should finish with a clean cut rather than a permanent forked interface model.

## 13. Phase 1 Deliverable

Phase 1 is complete when all of the following are true:

- a client can create or use a session
- a client can start a run
- a client can receive SSE events for that run
- a completed or failed run can be queried by `run_id`
- the runtime uses LiteLLM as the model access layer
- DeepAgents handles planning and skill execution
- LangGraph-backed session state is hidden behind runtime/session abstractions

## 14. Testing Strategy

The first implementation plan should require coverage for:

- request validation for runs and sessions
- SSE event sequence correctness
- run lifecycle transitions
- session to graph-thread mapping behavior
- provider error propagation
- runtime event normalization
- cancellation and timeout behavior where supported

Testing should combine:

- focused unit tests for runtime, providers, and event normalization
- integration tests for the FastAPI endpoints and SSE stream behavior

## 15. Acceptance Summary

This design is considered accepted if the user agrees with:

- FastAPI as the sole runtime host
- `session/run/event` as the public model
- LiteLLM, DeepAgents, and LangGraph as separated responsibilities
- SSE-first streaming for phase 1
- an incremental migration that ends by deleting the old chat API

Once accepted, the next step is to create a detailed implementation plan for Phase 1.
