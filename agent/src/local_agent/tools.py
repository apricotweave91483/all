from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import shutil
import subprocess

from .config import AgentConfig
from .safety import classify_command

PLACEHOLDER_VALUES = {
    "relative path",
    "regex or plain text",
    "shell command",
    "target text",
    "replacement text",
    "...full file contents...",
}


@dataclass(slots=True)
class ToolResult:
    output: str
    changed_paths: tuple[str, ...] = ()


@dataclass(slots=True)
class ToolRunner:
    config: AgentConfig

    def describe_workspace(self) -> str:
        return self._render_tree(self.config.cwd, depth=2, max_entries=80)

    def schema_text(self) -> str:
        return json.dumps(
            {
                "tools": [
                    {
                        "name": "list_dir",
                        "args": {"path": "relative path", "recursive": False},
                    },
                    {
                        "name": "read_file",
                        "args": {
                            "path": "relative path",
                            "start_line": 1,
                            "end_line": 200,
                        },
                    },
                    {
                        "name": "search",
                        "args": {
                            "pattern": "regex or plain text",
                            "path": ".",
                        },
                    },
                    {
                        "name": "write_file",
                        "args": {
                            "path": "relative path",
                            "content": "full file contents",
                        },
                    },
                    {
                        "name": "replace_in_file",
                        "args": {
                            "path": "relative path",
                            "old": "target text",
                            "new": "replacement text",
                            "count": 1,
                        },
                    },
                    {
                        "name": "run_shell",
                        "args": {
                            "command": "shell command",
                            "timeout_seconds": 180,
                        },
                    },
                ]
            },
            indent=2,
        )

    def run(self, tool_name: str, args: dict) -> ToolResult:
        if tool_name == "list_dir":
            return self.list_dir(
                args.get("path", "."), bool(args.get("recursive", False))
            )
        if tool_name == "read_file":
            return self.read_file(
                args["path"],
                int(args.get("start_line", 1)),
                args.get("end_line"),
            )
        if tool_name == "search":
            return self.search(args["pattern"], args.get("path", "."))
        if tool_name == "write_file":
            return self.write_file(args["path"], args["content"])
        if tool_name == "replace_in_file":
            return self.replace_in_file(
                args["path"],
                args["old"],
                args["new"],
                int(args.get("count", 1)),
            )
        if tool_name == "run_shell":
            return self.run_shell(
                args["command"],
                int(args.get("timeout_seconds", self.config.shell_timeout_seconds)),
            )
        raise ValueError(f"Unknown tool: {tool_name}")

    def list_dir(self, path: str, recursive: bool = False) -> ToolResult:
        placeholder_error = self._check_placeholder(path, "path")
        if placeholder_error:
            return ToolResult(placeholder_error)
        target = self._resolve_path(path)
        if not target.exists():
            return ToolResult(f"Path does not exist: {path}")
        if target.is_file():
            return ToolResult(f"{path} is a file, not a directory.")

        if recursive:
            return ToolResult(self._render_tree(target, depth=6, max_entries=300))

        entries: list[str] = []
        for child in sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name)):
            suffix = "/" if child.is_dir() else ""
            entries.append(f"{child.relative_to(self.config.cwd)}{suffix}")
        if not entries:
            return ToolResult(f"{path} is empty.")
        return ToolResult(self._truncate("\n".join(entries)))

    def read_file(self, path: str, start_line: int = 1, end_line: int | None = None) -> ToolResult:
        placeholder_error = self._check_placeholder(path, "path")
        if placeholder_error:
            return ToolResult(placeholder_error)
        target = self._resolve_path(path)
        if not target.exists():
            return ToolResult(f"File does not exist: {path}")
        if not target.is_file():
            return ToolResult(f"{path} is not a file.")

        text = target.read_text(encoding="utf-8")
        lines = text.splitlines()
        start_index = max(start_line - 1, 0)

        max_end = start_index + self.config.max_read_lines
        desired_end = len(lines) if end_line is None else max(int(end_line), start_line)
        final_end = min(desired_end, max_end, len(lines))

        chunk = lines[start_index:final_end]
        numbered = "\n".join(
            f"{line_number:4d}: {line}"
            for line_number, line in enumerate(chunk, start=start_index + 1)
        )

        suffix = ""
        if final_end < desired_end:
            suffix = (
                f"\n[truncated at {self.config.max_read_lines} lines; request a later range]"
            )
        return ToolResult(self._truncate(numbered + suffix))

    def search(self, pattern: str, path: str = ".") -> ToolResult:
        placeholder_error = self._check_placeholder(pattern, "pattern")
        if placeholder_error:
            return ToolResult(placeholder_error)
        path_error = self._check_placeholder(path, "path")
        if path_error:
            return ToolResult(path_error)
        target = self._resolve_path(path)
        if shutil.which("rg"):
            process = subprocess.run(
                ["rg", "-n", "--hidden", "--glob", "!.git", pattern, str(target)],
                cwd=self.config.cwd,
                capture_output=True,
                text=True,
            )
            output = process.stdout if process.returncode in {0, 1} else process.stderr
            return ToolResult(self._truncate(output or "No matches."))

        matches: list[str] = []
        if target.is_file():
            candidates = [target]
        else:
            candidates = [
                file_path
                for file_path in target.rglob("*")
                if file_path.is_file() and ".git" not in file_path.parts
            ]

        for file_path in candidates:
            try:
                for line_number, line in enumerate(
                    file_path.read_text(encoding="utf-8").splitlines(), start=1
                ):
                    if pattern in line:
                        matches.append(
                            f"{file_path.relative_to(self.config.cwd)}:{line_number}:{line}"
                        )
            except UnicodeDecodeError:
                continue

        return ToolResult(self._truncate("\n".join(matches) if matches else "No matches."))

    def write_file(self, path: str, content: str) -> ToolResult:
        placeholder_error = self._check_placeholder(path, "path")
        if placeholder_error:
            return ToolResult(placeholder_error)
        content_error = self._check_placeholder(content, "content")
        if content_error:
            return ToolResult(content_error)
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        previous = None
        if target.exists():
            previous = target.read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")

        if previous == content:
            return ToolResult(f"No changes written to {path}.")
        if previous is None:
            return ToolResult(
                f"Created {path} ({len(content)} bytes).",
                changed_paths=(path,),
            )
        return ToolResult(
            f"Updated {path} ({len(content)} bytes).",
            changed_paths=(path,),
        )

    def replace_in_file(self, path: str, old: str, new: str, count: int = 1) -> ToolResult:
        placeholder_error = self._check_placeholder(path, "path")
        if placeholder_error:
            return ToolResult(placeholder_error)
        old_error = self._check_placeholder(old, "old")
        if old_error:
            return ToolResult(old_error)
        new_error = self._check_placeholder(new, "new")
        if new_error:
            return ToolResult(new_error)
        target = self._resolve_path(path)
        if not target.exists():
            return ToolResult(f"File does not exist: {path}")
        text = target.read_text(encoding="utf-8")
        occurrences = text.count(old)
        if occurrences == 0:
            return ToolResult("Target text not found.")

        limit = count if count > 0 else occurrences
        updated = text.replace(old, new, limit)
        target.write_text(updated, encoding="utf-8")
        return ToolResult(
            f"Updated {path}; replaced {min(occurrences, limit)} occurrence(s).",
            changed_paths=(path,),
        )

    def run_shell(self, command: str, timeout_seconds: int) -> ToolResult:
        placeholder_error = self._check_placeholder(command, "command")
        if placeholder_error:
            return ToolResult(placeholder_error)
        decision = classify_command(command)
        if decision.should_ask and not self.config.auto_approve_risky_shell:
            print(f"Approval required: {command}")
            print(f"Reason: {decision.reason}")
            answer = input("Run this shell command? [y/N]: ").strip().lower()
            if answer not in {"y", "yes"}:
                return ToolResult("Shell command not approved by the user.")

        shell_path = os.environ.get("SHELL") or "/bin/bash"
        try:
            process = subprocess.run(
                command,
                cwd=self.config.cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=True,
                executable=shell_path,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(f"Shell command timed out after {timeout_seconds} seconds.")

        output = (
            f"exit_code={process.returncode}\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        ).strip()
        return ToolResult(self._truncate(output))

    def _resolve_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.config.cwd / candidate).resolve()

        try:
            resolved.relative_to(self.config.cwd)
        except ValueError as exc:
            raise ValueError(
                f"Path escapes the workspace root: {raw_path}"
            ) from exc
        return resolved

    def _render_tree(self, root: Path, depth: int, max_entries: int) -> str:
        results: list[str] = []

        def visit(current: Path, current_depth: int) -> None:
            if len(results) >= max_entries or current_depth > depth:
                return
            for child in sorted(current.iterdir(), key=lambda item: (item.is_file(), item.name)):
                if child.name == ".git":
                    continue
                relative = child.relative_to(self.config.cwd)
                indent = "  " * current_depth
                suffix = "/" if child.is_dir() else ""
                results.append(f"{indent}{relative}{suffix}")
                if child.is_dir():
                    visit(child, current_depth + 1)
                if len(results) >= max_entries:
                    return

        visit(root, 0)
        if not results:
            return "."
        return "\n".join(results)

    def _truncate(self, text: str) -> str:
        text = text.strip() or "(no output)"
        if len(text) <= self.config.max_tool_output_chars:
            return text
        clipped = text[: self.config.max_tool_output_chars]
        return f"{clipped}\n[truncated]"

    def _check_placeholder(self, value: str, field_name: str) -> str | None:
        normalized = value.strip()
        if normalized in PLACEHOLDER_VALUES:
            return (
                f"Tool error: placeholder value {normalized!r} was provided for {field_name}. "
                f"Use a real workspace path, search pattern, file content, or shell command."
            )
        return None
