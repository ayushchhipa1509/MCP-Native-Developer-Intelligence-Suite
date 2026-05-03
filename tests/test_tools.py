"""Unit tests for the Developer Intelligence tools.

Tests GitAnalyzer and CodeAuditor against the project's own codebase.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tools.code_auditor import CodeAuditor, CodeStructureParams
from tools.git_analyzer import GitAnalyzer, GitHistoryParams


# ─── Git Analyzer Tests ───────────────────────────────────────────


class TestGitHistoryParams:
    """Validate Pydantic schema enforcement for GitHistoryParams."""

    def test_rejects_nonexistent_path(self):
        with pytest.raises(ValueError, match="does not exist"):
            GitHistoryParams(repo_path="/nonexistent/path")

    def test_rejects_non_repo(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Not a git repository"):
            GitHistoryParams(repo_path=str(tmp_path))

    def test_rejects_excessive_commits(self):
        with pytest.raises(ValueError):
            GitHistoryParams(repo_path=".", num_commits=1000)

    def test_rejects_zero_commits(self):
        with pytest.raises(ValueError):
            GitHistoryParams(repo_path=".", num_commits=0)


class TestGitAnalyzer:
    """Test GitAnalyzer against this project's own git repo."""

    @pytest.fixture
    def analyzer(self) -> GitAnalyzer:
        # Use the project root (assumes tests are run from repo root)
        project_root = Path(__file__).parent.parent
        return GitAnalyzer(str(project_root))

    def test_get_history_returns_list(self, analyzer: GitAnalyzer):
        history = analyzer.get_history(num_commits=5)
        assert isinstance(history, list)

    def test_commit_has_required_fields(self, analyzer: GitAnalyzer):
        history = analyzer.get_history(num_commits=1)
        if history:
            commit = history[0]
            assert "hash" in commit
            assert "author_name" in commit
            assert "author_email" in commit
            assert "date" in commit
            assert "message" in commit

    def test_to_json_returns_valid_json(self, analyzer: GitAnalyzer):
        result = analyzer.to_json(num_commits=3)
        parsed = json.loads(result)
        assert "commits" in parsed
        assert "contributors" in parsed


# ─── Code Auditor Tests ───────────────────────────────────────────


class TestCodeStructureParams:
    """Validate Pydantic schema enforcement for CodeStructureParams."""

    def test_rejects_nonexistent_directory(self):
        with pytest.raises(ValueError, match="does not exist"):
            CodeStructureParams(directory_path="/nonexistent/dir")

    def test_rejects_file_path(self, tmp_path: Path):
        file = tmp_path / "test.py"
        file.write_text("x = 1")
        with pytest.raises(ValueError, match="not a directory"):
            CodeStructureParams(directory_path=str(file))


class TestCodeAuditor:
    """Test CodeAuditor against a known Python file."""

    @pytest.fixture
    def sample_dir(self, tmp_path: Path) -> Path:
        code = '''
class Animal:
    """Base animal class."""
    name: str

    def speak(self) -> str:
        return "..."

class Dog(Animal):
    """A dog."""
    def speak(self) -> str:
        return "Woof!"

def helper_function(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y
'''
        (tmp_path / "sample.py").write_text(code)
        return tmp_path

    def test_analyze_finds_classes(self, sample_dir: Path):
        auditor = CodeAuditor(str(sample_dir))
        result = auditor.analyze()
        assert result["summary"]["total_classes"] == 2

    def test_analyze_finds_functions(self, sample_dir: Path):
        auditor = CodeAuditor(str(sample_dir))
        result = auditor.analyze()
        assert result["summary"]["total_functions"] == 1

    def test_class_hierarchy_correct(self, sample_dir: Path):
        auditor = CodeAuditor(str(sample_dir))
        result = auditor.analyze()
        assert "Dog" in result["class_hierarchy"]
        assert "Animal" in result["class_hierarchy"]["Dog"]

    def test_to_json_valid(self, sample_dir: Path):
        auditor = CodeAuditor(str(sample_dir))
        parsed = json.loads(auditor.to_json())
        assert "summary" in parsed
        assert "files" in parsed
        assert "dependency_map" in parsed
