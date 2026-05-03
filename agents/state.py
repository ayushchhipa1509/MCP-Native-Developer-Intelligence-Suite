"""LangGraph state definitions for the Developer Intelligence Suite.

Defines the shared TypedDict that flows through the Scout → Historian →
Synthesizer state machine. All fields use total=False so nodes can
return partial state updates.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state flowing through the LangGraph state machine.

    Attributes:
        project_path: Absolute path to the target project directory.
        discovered_files: File manifest produced by the Scout node,
            containing path, size, and extension metadata.
        git_context: Structured git history and contributor data
            produced by the Historian node.
        analysis_results: AST-based code structure analysis output
            produced by the Scout's code auditing pass.
        final_report: The synthesized Markdown intelligence report
            produced by the Synthesizer node.
        errors: Accumulator for any errors encountered during execution.
    """

    project_path: str
    discovered_files: list[dict[str, Any]]
    git_context: dict[str, Any]
    analysis_results: dict[str, Any]
    final_report: str
    errors: list[str]
