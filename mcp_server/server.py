"""Core MCP Server implementation with tool registration.

Defines the 'developer-intel-suite' MCP Server using the low-level
Server class. All tool input schemas are derived from Pydantic models
for strict validation. Tool dispatch is handled via pattern matching.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from tools.code_auditor import CodeAuditor, CodeStructureParams
from tools.git_analyzer import GitAnalyzer, GitHistoryParams

logger = logging.getLogger(__name__)


# ─── Tool Registry ─────────────────────────────────────────────────

TOOLS: list[Tool] = [
    Tool(
        name="get_git_history",
        description=(
            "Extract the last N commits from a Git repository, including "
            "commit hashes, author metadata (name + email), ISO timestamps, "
            "commit messages, and diff statistics (files changed, insertions, "
            "deletions). Also returns contributor summary."
        ),
        inputSchema=GitHistoryParams.model_json_schema(),
    ),
    Tool(
        name="analyze_code_structure",
        description=(
            "Perform AST-based static analysis on a Python codebase directory. "
            "Maps class hierarchies, function signatures, import dependencies, "
            "and generates aggregate code metrics (LOC, class count, etc.)."
        ),
        inputSchema=CodeStructureParams.model_json_schema(),
    ),
]


# ─── Server Factory ────────────────────────────────────────────────


def create_server() -> Server:
    """Factory function to create and configure the MCP server instance.

    Registers tool listing and tool dispatch handlers on the server.
    Returns the configured Server ready to be run with a transport.
    """
    server = Server("developer-intel-suite")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Expose all registered tools to the MCP host."""
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Dispatch incoming tool calls to their implementations."""
        try:
            result = _dispatch_tool(name, arguments)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.exception("Tool execution failed: %s", name)
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "tool": name}),
            )]

    return server


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    """Route tool calls to their concrete implementations with validation."""
    match name:
        case "get_git_history":
            params = GitHistoryParams(**arguments)
            analyzer = GitAnalyzer(params.repo_path)
            return analyzer.to_json(params.num_commits)

        case "analyze_code_structure":
            params = CodeStructureParams(**arguments)
            auditor = CodeAuditor(params.directory_path, params.file_extensions)
            return auditor.to_json()

        case _:
            raise ValueError(f"Unknown tool: {name}")
