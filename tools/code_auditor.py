"""AST-based static analysis module for Python codebases.

Walks the Abstract Syntax Tree of every Python file in a directory
to extract class hierarchies, function signatures, import graphs,
and aggregate code metrics.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ─── Pydantic Schemas ──────────────────────────────────────────────


class CodeStructureParams(BaseModel):
    """Validated input schema for the analyze_code_structure MCP tool."""

    directory_path: str = Field(
        ...,
        description="Absolute path to the directory to analyze.",
    )
    file_extensions: list[str] = Field(
        default=[".py"],
        description="File extensions to include in analysis.",
    )

    @field_validator("directory_path")
    @classmethod
    def validate_directory(cls, v: str) -> str:
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return str(path.resolve())


# ─── AST Visitor ───────────────────────────────────────────────────


class StructureVisitor(ast.NodeVisitor):
    """Custom AST visitor extracting structural metadata from Python source."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.classes: list[dict[str, Any]] = []
        self.functions: list[dict[str, Any]] = []
        self.imports: list[dict[str, Any]] = []
        self._current_class: str | None = None

    # ── Class definitions ──────────────────────────────────────

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [self._resolve_name(b) for b in node.bases]
        methods: list[dict[str, Any]] = []
        class_vars: list[dict[str, Any]] = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in item.args.args if a.arg != "self"]
                methods.append({
                    "name": item.name,
                    "args": args,
                    "return_type": self._resolve_annotation(item.returns),
                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                    "decorators": [self._resolve_name(d) for d in item.decorator_list],
                    "line": item.lineno,
                })
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                class_vars.append({
                    "name": item.target.id,
                    "type": self._resolve_annotation(item.annotation),
                })

        self.classes.append({
            "name": node.name,
            "bases": bases,
            "methods": methods,
            "class_variables": class_vars,
            "decorators": [self._resolve_name(d) for d in node.decorator_list],
            "line": node.lineno,
            "docstring": ast.get_docstring(node),
        })

        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = None

    # ── Function definitions ───────────────────────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._current_class is not None:
            return  # Methods are captured inside visit_ClassDef
        self._record_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self._current_class is not None:
            return
        self._record_function(node)
        self.generic_visit(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        args = [a.arg for a in node.args.args]
        self.functions.append({
            "name": node.name,
            "args": args,
            "return_type": self._resolve_annotation(node.returns),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "decorators": [self._resolve_name(d) for d in node.decorator_list],
            "line": node.lineno,
            "docstring": ast.get_docstring(node),
        })

    # ── Import statements ──────────────────────────────────────

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append({
                "type": "import",
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.imports.append({
                "type": "from_import",
                "module": module,
                "name": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })

    # ── Name resolution helpers ────────────────────────────────

    @staticmethod
    def _resolve_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{StructureVisitor._resolve_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return StructureVisitor._resolve_name(node.func)
        return ast.dump(node)

    @staticmethod
    def _resolve_annotation(node: ast.expr | None) -> str | None:
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{StructureVisitor._resolve_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            value = StructureVisitor._resolve_annotation(node.value)
            slice_val = StructureVisitor._resolve_annotation(node.slice)
            return f"{value}[{slice_val}]"
        return ast.dump(node)


# ─── Core Auditor ──────────────────────────────────────────────────


class CodeAuditor:
    """AST-based static analysis engine for Python codebases.

    Scans a directory for Python files, parses each via the ast module,
    and produces structured metadata: classes, functions, imports,
    dependency maps, and aggregate metrics.
    """

    def __init__(self, directory: str, extensions: list[str] | None = None) -> None:
        self._directory = Path(directory).resolve()
        self._extensions = extensions or [".py"]

    def _discover_files(self) -> list[Path]:
        """Recursively find source files, excluding hidden dirs and __pycache__."""
        files: list[Path] = []
        for ext in self._extensions:
            files.extend(self._directory.rglob(f"*{ext}"))
        return [
            f for f in sorted(files)
            if not any(
                part.startswith(".") or part == "__pycache__"
                for part in f.parts
            )
        ]

    def _analyze_file(self, file_path: Path) -> dict[str, Any]:
        """Parse a single file and extract its AST structure."""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            return {
                "file": str(file_path.relative_to(self._directory)),
                "error": str(e),
                "classes": [],
                "functions": [],
                "imports": [],
            }

        visitor = StructureVisitor(str(file_path))
        visitor.visit(tree)

        return {
            "file": str(file_path.relative_to(self._directory)),
            "lines_of_code": len(source.splitlines()),
            "classes": visitor.classes,
            "functions": visitor.functions,
            "imports": visitor.imports,
        }

    def analyze(self) -> dict[str, Any]:
        """Perform full structural analysis of the codebase.

        Returns a dict containing:
        - summary: aggregate metrics
        - files: per-file analysis results
        - dependency_map: file -> imported modules
        - class_hierarchy: class -> base classes
        """
        files = self._discover_files()
        file_analyses = [self._analyze_file(f) for f in files]

        total_classes = sum(len(fa["classes"]) for fa in file_analyses)
        total_functions = sum(len(fa["functions"]) for fa in file_analyses)
        total_loc = sum(fa.get("lines_of_code", 0) for fa in file_analyses)
        total_imports = sum(len(fa["imports"]) for fa in file_analyses)

        # Build dependency map: file -> list of imported modules
        dependency_map: dict[str, list[str]] = {}
        for fa in file_analyses:
            deps = sorted({imp.get("module", "") for imp in fa["imports"]})
            dependency_map[fa["file"]] = deps

        # Build class hierarchy: class_name -> list of base class names
        class_hierarchy: dict[str, list[str]] = {}
        for fa in file_analyses:
            for cls in fa["classes"]:
                class_hierarchy[cls["name"]] = cls["bases"]

        return {
            "summary": {
                "total_files": len(file_analyses),
                "total_classes": total_classes,
                "total_functions": total_functions,
                "total_lines_of_code": total_loc,
                "total_imports": total_imports,
            },
            "files": file_analyses,
            "dependency_map": dependency_map,
            "class_hierarchy": class_hierarchy,
        }

    def to_json(self) -> str:
        """Serialize analysis results to JSON."""
        return json.dumps(self.analyze(), indent=2, default=str)
