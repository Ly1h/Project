from __future__ import annotations

import ast
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, List

from .core import ToolRegistry, ToolResult


def _safe_path(workspace: Path, rel: str | Path) -> Path:
    workspace = workspace.resolve()
    path = (workspace / rel).resolve()
    if workspace not in path.parents and path != workspace:
        raise ValueError(f"Unsafe path outside workspace: {rel}")
    return path


def list_files(workspace: str, pattern: str = "*", limit: int = 200) -> ToolResult:
    root = Path(workspace).resolve()
    if not root.exists():
        return ToolResult(False, f"Workspace does not exist: {root}")
    files = []
    for p in root.rglob(pattern):
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts:
            files.append(str(p.relative_to(root)))
        if len(files) >= limit:
            break
    return ToolResult(True, "\n".join(files), {"count": len(files)})


def read_text(workspace: str, path: str, max_chars: int = 8000) -> ToolResult:
    try:
        p = _safe_path(Path(workspace), path)
        text = p.read_text(encoding="utf-8", errors="ignore")
        return ToolResult(True, text[:max_chars], {"path": str(p), "truncated": len(text) > max_chars})
    except Exception as exc:
        return ToolResult(False, str(exc))


def write_text(workspace: str, path: str, content: str) -> ToolResult:
    try:
        p = _safe_path(Path(workspace), path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(True, f"Wrote {p}", {"path": str(p), "chars": len(content)})
    except Exception as exc:
        return ToolResult(False, str(exc))


def grep_text(workspace: str, regex: str, include_suffixes: str = ".py,.md,.txt,.json,.yaml,.yml", limit: int = 100) -> ToolResult:
    root = Path(workspace).resolve()
    suffixes = {s.strip() for s in include_suffixes.split(",") if s.strip()}
    pattern = re.compile(regex, re.IGNORECASE)
    hits: List[str] = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in suffixes or ".git" in p.parts:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if pattern.search(line):
                    hits.append(f"{p.relative_to(root)}:{i}: {line.strip()}")
                    if len(hits) >= limit:
                        return ToolResult(True, "\n".join(hits), {"count": len(hits), "truncated": True})
        except Exception:
            continue
    return ToolResult(True, "\n".join(hits), {"count": len(hits), "truncated": False})


def ast_check_python(workspace: str) -> ToolResult:
    root = Path(workspace).resolve()
    errors = []
    checked = 0
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts or ".git" in p.parts:
            continue
        checked += 1
        try:
            ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            errors.append(f"{p.relative_to(root)}:{exc.lineno}: {exc.msg}")
    if errors:
        return ToolResult(False, "\n".join(errors), {"checked": checked, "errors": len(errors)})
    return ToolResult(True, f"AST check passed for {checked} Python files.", {"checked": checked})


def run_safe_command(workspace: str, command: str, timeout: int = 30) -> ToolResult:
    """Run a constrained command inside workspace."""
    allowed_prefixes = [
        "python -m pytest",
        "pytest",
        "python -m unittest",
        "python -m py_compile",
    ]
    if not any(command.strip().startswith(prefix) for prefix in allowed_prefixes):
        return ToolResult(False, f"Command blocked by allowlist: {command}", {"allowed": allowed_prefixes})
    try:
        proc = subprocess.run(
            command,
            cwd=Path(workspace).resolve(),
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return ToolResult(proc.returncode == 0, out, {"returncode": proc.returncode})
    except subprocess.TimeoutExpired:
        return ToolResult(False, f"Command timed out after {timeout}s", {"timeout": timeout})
    except Exception as exc:
        return ToolResult(False, str(exc))


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("list_files", list_files)
    reg.register("read_text", read_text)
    reg.register("write_text", write_text)
    reg.register("grep_text", grep_text)
    reg.register("ast_check_python", ast_check_python)
    reg.register("run_safe_command", run_safe_command)
    return reg
