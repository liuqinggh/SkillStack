"""Build LangChain tools from MCP server configuration."""

from __future__ import annotations

import asyncio
from typing import Any

from csbot.config.settings import McpConfig
from csbot.domain.errors import ConfigError


async def _load_tools_async(config: McpConfig) -> list[Any]:
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as e:
        raise ConfigError(
            "MCP is enabled but dependency 'langchain-mcp-adapters' is missing. "
            "Install it via pip before enabling mcp.enabled=true."
        ) from e

    server_specs: dict[str, dict[str, Any]] = {}
    for server in config.servers:
        spec: dict[str, Any] = {"transport": server.transport}
        if server.transport == "stdio":
            spec["command"] = server.command
            spec["args"] = server.args
            if server.env:
                spec["env"] = server.env
        else:
            spec["url"] = server.url
        server_specs[server.name] = spec

    client = MultiServerMCPClient(server_specs)
    tools = await asyncio.wait_for(client.get_tools(), timeout=config.startup_timeout_sec)
    return list(tools)


def build_mcp_tools(config: McpConfig) -> list[Any]:
    """Load MCP tools for DeepAgents `tools=` injection."""
    if not config.enabled or not config.servers:
        return []
    try:
        return asyncio.run(_load_tools_async(config))
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f"Failed to initialize MCP tools: {e}") from e
