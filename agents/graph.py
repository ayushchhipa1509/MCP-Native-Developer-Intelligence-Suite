"""LangGraph state machine for multi-agent developer intelligence orchestration.

Implements three nodes:
    Scout      — Discovers project files and performs AST analysis.
    Historian  — Extracts git history and contributor patterns.
    Synthesizer — Aggregates all intelligence into a Markdown report.

The graph executes linearly: Scout → Historian → Synthesizer → END.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from agents.state import AgentState
from tools.code_auditor import CodeAuditor
from tools.git_analyzer import GitAnalyzer

logger = logging.getLogger(__name__)


# ─── Node: Scout ───────────────────────────────────────────────────


def scout_node(state: AgentState) -> dict[str, Any]:
    """Scout Node: Discover project files and perform code structure analysis.

    Scans the target project directory for source files, builds a manifest,
    and runs AST-based analysis on all discovered Python files.
    """
    project_path = state["project_path"]
    errors: list[str] = list(state.get("errors", []))

    logger.info("Scout: Scanning project at %s", project_path)

    try:
        root = Path(project_path).resolve()
        if not root.exists():
            errors.append(f"Project path does not exist: {project_path}")
            return {"discovered_files": [], "analysis_results": {}, "errors": errors}

        # Discover all source files
        source_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".h"}
        discovered: list[dict[str, Any]] = []

        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            if any(part.startswith(".") or part == "__pycache__" for part in file_path.parts):
                continue
            if file_path.suffix in source_extensions:
                discovered.append({
                    "path": str(file_path.relative_to(root)),
                    "extension": file_path.suffix,
                    "size_bytes": file_path.stat().st_size,
                })

        logger.info("Scout: Discovered %d source files", len(discovered))

        # Run AST analysis on the project
        auditor = CodeAuditor(str(root))
        analysis = auditor.analyze()

        return {
            "discovered_files": discovered,
            "analysis_results": analysis,
            "errors": errors,
        }

    except Exception as e:
        logger.exception("Scout node failed")
        errors.append(f"Scout error: {e}")
        return {"discovered_files": [], "analysis_results": {}, "errors": errors}


# ─── Node: Historian ───────────────────────────────────────────────


def historian_node(state: AgentState) -> dict[str, Any]:
    """Historian Node: Extract and structure git history data.

    Queries the Git repository for recent commits, diff statistics,
    and contributor patterns. Stores structured results in state.
    """
    project_path = state["project_path"]
    errors: list[str] = list(state.get("errors", []))

    logger.info("Historian: Analyzing git history at %s", project_path)

    try:
        analyzer = GitAnalyzer(project_path)
        commits = analyzer.get_history(num_commits=25)
        contributors = analyzer.get_contributors()

        # Compute activity summary
        authors = {}
        for commit in commits:
            name = commit["author_name"]
            if name not in authors:
                authors[name] = {"commits": 0, "insertions": 0, "deletions": 0}
            authors[name]["commits"] += 1
            authors[name]["insertions"] += commit.get("insertions", 0)
            authors[name]["deletions"] += commit.get("deletions", 0)

        git_context = {
            "total_commits_analyzed": len(commits),
            "commits": commits,
            "contributors": contributors,
            "activity_by_author": authors,
        }

        logger.info("Historian: Analyzed %d commits from %d contributors",
                     len(commits), len(contributors))

        return {"git_context": git_context, "errors": errors}

    except Exception as e:
        logger.exception("Historian node failed")
        errors.append(f"Historian error: {e}")
        return {"git_context": {}, "errors": errors}


# ─── Node: Synthesizer ────────────────────────────────────────────


def synthesizer_node(state: AgentState) -> dict[str, Any]:
    """Synthesizer Node: Aggregate all intelligence into a final report.

    Combines Scout's file discovery, code analysis, and Historian's
    git context into a comprehensive Markdown intelligence report.
    """
    logger.info("Synthesizer: Generating final intelligence report")

    project_path = state.get("project_path", "Unknown")
    discovered = state.get("discovered_files", [])
    analysis = state.get("analysis_results", {})
    git_ctx = state.get("git_context", {})
    errors = list(state.get("errors", []))

    summary = analysis.get("summary", {})
    commits = git_ctx.get("commits", [])
    contributors = git_ctx.get("contributors", [])
    class_hierarchy = analysis.get("class_hierarchy", {})
    activity = git_ctx.get("activity_by_author", {})

    # ── Build the Markdown report ──

    lines: list[str] = [
        f"# 📊 Developer Intelligence Report",
        f"",
        f"**Project:** `{project_path}`  ",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}  ",
        f"**Status:** {'⚠️ Completed with errors' if errors else '✅ Clean'}",
        f"",
        f"---",
        f"",
        f"## 📁 Project Overview",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Source Files | {len(discovered)} |",
        f"| Python Files | {summary.get('total_files', 'N/A')} |",
        f"| Total LOC | {summary.get('total_lines_of_code', 'N/A'):,} |"
        if isinstance(summary.get('total_lines_of_code'), int)
        else f"| Total LOC | {summary.get('total_lines_of_code', 'N/A')} |",
        f"| Classes | {summary.get('total_classes', 'N/A')} |",
        f"| Functions | {summary.get('total_functions', 'N/A')} |",
        f"| Import Statements | {summary.get('total_imports', 'N/A')} |",
        f"",
    ]

    # File breakdown by extension
    ext_counts: dict[str, int] = {}
    for f in discovered:
        ext = f.get("extension", "unknown")
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    if ext_counts:
        lines.extend([
            f"### File Distribution",
            f"",
            f"| Extension | Count |",
            f"|-----------|-------|",
        ])
        for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| `{ext}` | {count} |")
        lines.append("")

    # Class hierarchy
    if class_hierarchy:
        lines.extend([
            f"## 🏗️ Class Hierarchy",
            f"",
            f"```",
        ])
        for cls_name, bases in sorted(class_hierarchy.items()):
            bases_str = ", ".join(bases) if bases else "object"
            lines.append(f"  {cls_name} → {bases_str}")
        lines.extend(["```", ""])

    # Git history
    lines.extend([
        f"## 📜 Git History (Last {len(commits)} commits)",
        f"",
    ])

    if commits:
        lines.extend([
            f"| Hash | Author | Date | Message |",
            f"|------|--------|------|---------|",
        ])
        for c in commits[:15]:  # Cap table at 15 rows for readability
            short_hash = c["hash"][:8]
            lines.append(
                f"| `{short_hash}` | {c['author_name']} | {c['date'][:10]} | {c['message'][:60]} |"
            )
        lines.append("")

    # Contributor stats
    if contributors:
        lines.extend([
            f"## 👥 Contributors",
            f"",
            f"| Author | Commits |",
            f"|--------|---------|",
        ])
        for contrib in contributors:
            lines.append(f"| {contrib['author']} | {contrib['commits']} |")
        lines.append("")

    # Errors section
    if errors:
        lines.extend([
            f"## ⚠️ Errors Encountered",
            f"",
        ])
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.extend([
        "---",
        f"*Report generated by MCP Developer Intelligence Suite*",
    ])

    final_report = "\n".join(lines)

    return {"final_report": final_report, "errors": errors}


# ─── Graph Assembly ────────────────────────────────────────────────


def build_graph() -> StateGraph:
    """Construct and return the compiled LangGraph state machine.

    Flow: Scout → Historian → Synthesizer → END
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("scout", scout_node)
    graph.add_node("historian", historian_node)
    graph.add_node("synthesizer", synthesizer_node)

    # Wire edges (linear pipeline)
    graph.set_entry_point("scout")
    graph.add_edge("scout", "historian")
    graph.add_edge("historian", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph


def create_app():
    """Build and compile the graph into a runnable app."""
    graph = build_graph()
    return graph.compile()


# ─── Convenience Runner ───────────────────────────────────────────


def run_intelligence_report(project_path: str) -> str:
    """Execute the full intelligence pipeline and return the Markdown report.

    Args:
        project_path: Absolute path to the target project.

    Returns:
        A formatted Markdown intelligence report string.
    """
    app = create_app()
    initial_state: AgentState = {
        "project_path": project_path,
        "errors": [],
    }
    result = app.invoke(initial_state)
    return result.get("final_report", "Error: No report generated.")
