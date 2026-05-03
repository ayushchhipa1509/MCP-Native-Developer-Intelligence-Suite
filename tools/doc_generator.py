"""Markdown documentation synthesis from code analysis data.

Takes the output of CodeAuditor and GitAnalyzer and produces
clean, navigable Markdown documentation for a project.
"""

from __future__ import annotations

from typing import Any


class DocGenerator:
    """Generates Markdown documentation from analysis artifacts.

    Accepts structured dicts from CodeAuditor.analyze() and
    GitAnalyzer.get_history() to produce human-readable docs.
    """

    def __init__(
        self,
        project_name: str,
        code_analysis: dict[str, Any] | None = None,
        git_history: list[dict[str, Any]] | None = None,
    ) -> None:
        self._project_name = project_name
        self._code_analysis = code_analysis or {}
        self._git_history = git_history or []

    def generate_api_docs(self) -> str:
        """Generate API reference documentation from AST analysis."""
        lines: list[str] = [
            f"# API Reference — {self._project_name}",
            "",
        ]

        files = self._code_analysis.get("files", [])
        for file_info in files:
            file_path = file_info.get("file", "unknown")
            classes = file_info.get("classes", [])
            functions = file_info.get("functions", [])

            if not classes and not functions:
                continue

            lines.extend([f"## `{file_path}`", ""])

            for cls in classes:
                bases = ", ".join(cls["bases"]) if cls["bases"] else "object"
                lines.extend([
                    f"### class `{cls['name']}` ({bases})",
                    "",
                ])
                if cls.get("docstring"):
                    lines.extend([f"> {cls['docstring']}", ""])

                for method in cls.get("methods", []):
                    args_str = ", ".join(method["args"])
                    ret = f" → {method['return_type']}" if method.get("return_type") else ""
                    prefix = "async " if method.get("is_async") else ""
                    lines.append(f"- `{prefix}{method['name']}({args_str}){ret}`")
                lines.append("")

            for func in functions:
                args_str = ", ".join(func["args"])
                ret = f" → {func['return_type']}" if func.get("return_type") else ""
                prefix = "async " if func.get("is_async") else ""
                lines.extend([
                    f"### `{prefix}{func['name']}({args_str}){ret}`",
                    "",
                ])
                if func.get("docstring"):
                    lines.extend([f"> {func['docstring']}", ""])

        return "\n".join(lines)

    def generate_changelog(self) -> str:
        """Generate a changelog from git history."""
        lines: list[str] = [
            f"# Changelog — {self._project_name}",
            "",
        ]

        for commit in self._git_history:
            date = commit.get("date", "unknown")[:10]
            message = commit.get("message", "No message")
            author = commit.get("author_name", "Unknown")
            short_hash = commit.get("hash", "")[:8]

            lines.append(f"- **[{short_hash}]** {message} — *{author}* ({date})")

        return "\n".join(lines)

    def generate_full(self) -> str:
        """Generate complete project documentation."""
        sections = [
            self.generate_api_docs(),
            "---",
            self.generate_changelog(),
        ]
        return "\n\n".join(sections)
