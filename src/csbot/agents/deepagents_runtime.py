"""DeepAgents graph wrapper: builds the agent from Settings + LLM provider mapping."""

from __future__ import annotations

from collections.abc import Iterator

from deepagents import create_deep_agent
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from csbot.adapters.sandbox_adapter import LocalSandboxBackend
from csbot.agents.mcp_tools import build_mcp_tools
from csbot.config.settings import AgentProfileConfig, Settings
from csbot.domain.errors import EngineError
from csbot.providers.base import LlmProvider


def extract_text_from_content(raw: object) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        text = ""
        for part in raw:
            if isinstance(part, dict):
                if part.get("type") == "text" and part.get("text"):
                    text += str(part["text"])
                elif "text" in part:
                    text += str(part["text"])
            elif isinstance(part, str) and part:
                text += part
        return text
    return str(raw) if raw else ""


def assistant_text_from_values_state(state: object) -> str:
    """Best-effort final assistant text from a LangGraph ``values`` stream payload (state dict).

    Used with ``stream_mode=["messages", "values"]`` so we can recover a reply in **one** graph
    run when token streaming yields no extractable deltas (instead of calling ``run_turn``, which
    would execute the graph again).

    If ``values`` events are missing or empty, :meth:`DeepAgentsRuntime.iter_stream_deltas` may
    still fall back to :meth:`DeepAgentsRuntime.run_turn` (second execution) — see that method.
    """
    if not isinstance(state, dict):
        return ""
    messages = state.get("messages")
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            text = extract_text_from_content(msg.content)
            if text:
                return text
    return ""


class DeepAgentsRuntime:
    """Owns the compiled DeepAgents graph and streaming/turn execution."""

    def __init__(self, settings: Settings, llm_provider: LlmProvider, *, profile: AgentProfileConfig) -> None:
        llm = ChatOpenAI(**llm_provider.openai_compatible_model_kwargs())
        mcp_tools = build_mcp_tools(settings.mcp)

        def backend_factory(_runtime) -> LocalSandboxBackend:
            return LocalSandboxBackend(settings.sandbox)

        self._chatbot = create_deep_agent(
            model=llm,
            tools=mcp_tools or None,
            system_prompt=profile.system_prompt,
            skills=profile.skills_sources,
            backend=backend_factory,
            memory=profile.memory_files,
            checkpointer=MemorySaver(),
        )

    def run_turn(self, user_input: str, session_id: str) -> str:
        try:
            input_state = {"messages": [HumanMessage(content=user_input)]}
            config = {"configurable": {"thread_id": session_id}}
            last_state: dict | None = None
            for chunk in self._chatbot.stream(input_state, config=config, stream_mode="values"):
                if isinstance(chunk, dict) and "messages" in chunk:
                    last_state = chunk
            if last_state is None:
                return ""
            return assistant_text_from_values_state(last_state)
        except Exception as e:
            raise EngineError(f"run_turn failed: {e}") from e

    def iter_stream_deltas(self, user_input: str, session_id: str) -> Iterator[str]:
        """Stream assistant text deltas from a **single** graph run when possible.

        Uses ``stream_mode=["messages", "values"]``. If message-token streaming produces no
        deltas, the final assistant text is taken from the last ``values`` chunk (same run).

        Falls back to :meth:`run_turn` only if the stream yields no ``values`` payload (unexpected
        for LangGraph; kept as a safety net — **that** path runs the graph a second time).
        """
        try:
            input_state = {"messages": [HumanMessage(content=user_input)]}
            config = {"configurable": {"thread_id": session_id}}

            accumulated = ""
            emitted_any = False
            last_values_state: dict | None = None

            for chunk in self._chatbot.stream(
                input_state,
                config=config,
                stream_mode=["messages", "values"],
            ):
                if isinstance(chunk, tuple) and len(chunk) == 2 and chunk[0] in (
                    "messages",
                    "values",
                ):
                    mode, payload = chunk
                    if mode == "values" and isinstance(payload, dict):
                        last_values_state = payload
                        continue
                    if mode == "messages":
                        msg = None
                        if isinstance(payload, tuple) and len(payload) >= 1:
                            msg = payload[0]
                        elif isinstance(payload, (AIMessage, AIMessageChunk)):
                            msg = payload
                        if not isinstance(msg, (AIMessage, AIMessageChunk)):
                            continue

                        current = extract_text_from_content(getattr(msg, "content", None))
                        if not current:
                            continue

                        if current.startswith(accumulated):
                            delta = current[len(accumulated) :]
                            accumulated = current
                        else:
                            delta = current
                            accumulated += current

                        if delta:
                            emitted_any = True
                            yield delta
                    continue

                # Older / unexpected shapes (e.g. plain message tuple without mode prefix)
                msg = None
                if isinstance(chunk, tuple) and len(chunk) >= 1:
                    msg = chunk[0]
                elif isinstance(chunk, (AIMessage, AIMessageChunk)):
                    msg = chunk
                if not isinstance(msg, (AIMessage, AIMessageChunk)):
                    continue

                current = extract_text_from_content(getattr(msg, "content", None))
                if not current:
                    continue

                if current.startswith(accumulated):
                    delta = current[len(accumulated) :]
                    accumulated = current
                else:
                    delta = current
                    accumulated += current

                if delta:
                    emitted_any = True
                    yield delta

            if not emitted_any:
                full = ""
                if last_values_state is not None:
                    full = assistant_text_from_values_state(last_values_state)
                if not full:
                    # Rare: no values chunk from LangGraph — run_turn re-executes the graph.
                    full = self.run_turn(user_input, session_id)
                if full:
                    yield full
        except EngineError:
            raise
        except Exception as e:
            raise EngineError(f"run_stream failed: {e}") from e
