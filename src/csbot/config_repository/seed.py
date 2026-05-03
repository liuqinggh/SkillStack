from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib

from .runtime_repository import (
    RuntimeAgentConfigRecord,
    RuntimeAgentProfileRecord,
    RuntimeAuthRecord,
    RuntimeLlmRecord,
    RuntimeMcpConfigRecord,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RuntimeSeedBundle:
    llm: RuntimeLlmRecord
    agent: RuntimeAgentConfigRecord
    mcp: RuntimeMcpConfigRecord
    auth: RuntimeAuthRecord


def default_runtime_seed(project_root: Path) -> RuntimeSeedBundle:
    return RuntimeSeedBundle(
        llm=RuntimeLlmRecord(
            provider="litellm",
            model="gemini-2.5-flash",
            base_url="http://127.0.0.1:4000/v1",
            api_key="sk-no-key-required",
            temperature=0.7,
            timeout_sec=60,
            max_tokens=8192,
        ),
        agent=RuntimeAgentConfigRecord(
            skill_manager_root=str(project_root.resolve()),
            thread_pool_workers=4,
            default_profile_id="default",
            profiles=[
                RuntimeAgentProfileRecord(
                    agent_id="default",
                    name="Default Agent",
                    system_prompt=(
                        "你是一个聪明、友好、乐于助人的聊天助手，也是一个由固定 system prompt 与固定 "
                        "skills 组成的应用级 agent。用自然、亲切的中文回复用户。保持对话连贯，有记忆力。"
                    ),
                    memory_files=["conversation_memory.json"],
                    skills_sources=["skills"],
                    enabled=True,
                    is_default=True,
                ),
                RuntimeAgentProfileRecord(
                    agent_id="skyro_claim",
                    name="Skyro Claim",
                    system_prompt=(
                        "你是 Skyro claim intake assistant，对外负责索赔资料收集与缺失项引导。"
                        "优先推进理赔收集和补件，不做无关泛化闲聊。"
                    ),
                    memory_files=["skyro_claim_memory.json"],
                    skills_sources=["skills/skyro-claim-chatbot", "skills/image-by-intent"],
                    enabled=True,
                    is_default=False,
                ),
                RuntimeAgentProfileRecord(
                    agent_id="image_by_intent",
                    name="Image By Intent",
                    system_prompt=(
                        "你是一个专门处理图片与 PDF 理解任务的助手。"
                        "默认根据用户意图识别、提取、总结图片或 PDF 内容。"
                    ),
                    memory_files=["image_by_intent_memory.json"],
                    skills_sources=["skills/image-by-intent"],
                    enabled=True,
                    is_default=False,
                ),
            ],
        ),
        mcp=RuntimeMcpConfigRecord(
            enabled=False,
            startup_timeout_sec=20,
            servers=[],
        ),
        auth=RuntimeAuthRecord(
            admin_email="admin@admin.com",
            password_hash=hash_password("123456"),
            admin_name="Admin",
            access_ttl_minutes=720,
        ),
    )
