"""Single-process agent bundle (方案 A: 固定能力包)."""

from __future__ import annotations

from dataclasses import dataclass

from csbot.config.settings import AgentConfig, AgentProfileConfig


@dataclass(frozen=True)
class DeploymentAgent:
    """本进程对外暴露的唯一 Agent：身份 + DeepAgents 所需的 profile 字段."""

    id: str
    profile: AgentProfileConfig


def load_deployment_agent(agent: AgentConfig) -> DeploymentAgent:
    """从配置解析当前部署的 Agent（始终使用 default_profile_id 对应的能力包）。"""
    profile = agent.deployment_profile()
    return DeploymentAgent(id=agent.default_profile_id, profile=profile)
