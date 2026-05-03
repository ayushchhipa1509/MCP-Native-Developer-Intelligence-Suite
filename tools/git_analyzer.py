"""Git CLI interaction module for repository intelligence.

Provides a high-performance wrapper around Git CLI commands using subprocess,
with Pydantic-validated inputs and structured output for MCP tool consumption.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ─── Pydantic Schemas ──────────────────────────────────────────────


class GitHistoryParams(BaseModel):
    """Validated input schema for the get_git_history MCP tool."""

    repo_path: str = Field(
        ...,
        description="Absolute path to the Git repository root.",
    )
    num_commits: int = Field(
        default=10,
        ge=1,
        le=500,
        description="Number of recent commits to retrieve.",
    )

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, v: str) -> str:
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Repository path does not exist: {v}")
        if not (path / ".git").exists():
            raise ValueError(f"Not a git repository: {v}")
        return str(path.resolve())


# ─── Core Analyzer ─────────────────────────────────────────────────


class GitAnalyzer:
    """High-performance Git CLI wrapper for repository intelligence.

    Executes Git commands via subprocess and parses output into
    structured dictionaries suitable for JSON serialization.
    """

    COMMIT_DELIMITER = "---COMMIT_BOUNDARY---"
    LOG_FORMAT = "%H%n%an%n%ae%n%aI%n%s"

    def __init__(self, repo_path: str) -> None:
        self._repo_path = Path(repo_path).resolve()
        self._validate_repo()

    def _validate_repo(self) -> None:
        """Ensure the path is a valid Git repository."""
        if not (self._repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {self._repo_path}")

    def _run_git(self, *args: str, timeout: int = 30) -> str:
        """Execute a Git CLI command and return stdout."""
        result = subprocess.run(
            ["git", *args],
            cwd=str(self._repo_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def get_history(self, num_commits: int = 10) -> list[dict[str, Any]]:
        """Extract the last N commits with metadata and diff statistics.

        Returns a list of commit records with hash, author info,
        timestamp, message, and file change statistics.
        """
        format_str = f"{self.LOG_FORMAT}%n{self.COMMIT_DELIMITER}"
        log_output = self._run_git(
            "log",
            f"-{num_commits}",
            f"--format={format_str}",
            "--stat",
        )

        commits: list[dict[str, Any]] = []
        raw_commits = log_output.split(self.COMMIT_DELIMITER)

        for raw in raw_commits:
            raw = raw.strip()
            if not raw:
                continue

            lines = raw.split("\n")
            if len(lines) < 5:
                continue

            # Parse formatted fields
            commit_hash = lines[0].strip()
            author_name = lines[1].strip()
            author_email = lines[2].strip()
            date = lines[3].strip()
            message = lines[4].strip()

            # Parse --stat output from remaining lines
            files_changed, insertions, deletions = 0, 0, 0
            diff_parts: list[str] = []

            for stat_line in lines[5:]:
                stat_line = stat_line.strip()
                if not stat_line:
                    continue
                if "file" in stat_line and "changed" in stat_line:
                    for part in stat_line.split(","):
                        part = part.strip()
                        if "file" in part:
                            files_changed = int(part.split()[0])
                        elif "insertion" in part:
                            insertions = int(part.split()[0])
                        elif "deletion" in part:
                            deletions = int(part.split()[0])
                else:
                    diff_parts.append(stat_line)

            commits.append({
                "hash": commit_hash,
                "author_name": author_name,
                "author_email": author_email,
                "date": date,
                "message": message,
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
                "diff_summary": "\n".join(diff_parts),
            })

        return commits

    def get_diff(self, commit_hash: str) -> str:
        """Get the full diff for a specific commit."""
        return self._run_git("diff", f"{commit_hash}~1", commit_hash)

    def get_file_history(self, file_path: str, num_commits: int = 10) -> list[dict[str, Any]]:
        """Get commit history scoped to a specific file."""
        format_str = f"{self.LOG_FORMAT}%n{self.COMMIT_DELIMITER}"
        log_output = self._run_git(
            "log", f"-{num_commits}", f"--format={format_str}",
            "--follow", "--", file_path,
        )

        commits: list[dict[str, Any]] = []
        for raw in log_output.split(self.COMMIT_DELIMITER):
            raw = raw.strip()
            if not raw:
                continue
            lines = raw.split("\n")
            if len(lines) < 5:
                continue
            commits.append({
                "hash": lines[0].strip(),
                "author_name": lines[1].strip(),
                "author_email": lines[2].strip(),
                "date": lines[3].strip(),
                "message": lines[4].strip(),
            })

        return commits

    def get_contributors(self) -> list[dict[str, Any]]:
        """Get contributor statistics sorted by commit count."""
        output = self._run_git("shortlog", "-sne", "HEAD")
        contributors: list[dict[str, Any]] = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) == 2:
                contributors.append({
                    "commits": int(parts[0].strip()),
                    "author": parts[1].strip(),
                })
        return contributors

    def to_json(self, num_commits: int = 10) -> str:
        """Serialize full git history analysis to JSON."""
        return json.dumps({
            "commits": self.get_history(num_commits),
            "contributors": self.get_contributors(),
        }, indent=2, default=str)
