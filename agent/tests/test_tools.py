from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_agent.config import AgentConfig
from local_agent.cli import (
    _action_signature,
    _goal_requires_workspace_changes,
    _normalize_action,
)
from local_agent.tools import ToolRunner


class ToolValidationTests(unittest.TestCase):
    def test_goal_requires_changes_for_write_task(self) -> None:
        self.assertTrue(
            _goal_requires_workspace_changes("please write a readme that explains the script")
        )

    def test_goal_does_not_require_changes_for_verify_task(self) -> None:
        self.assertFalse(
            _goal_requires_workspace_changes("please verify no syntax errors in the python file")
        )

    def test_normalize_shorthand_tool_action(self) -> None:
        action = _normalize_action(
            {
                "type": "write_file",
                "args": {"path": "app.py", "content": "print('hi')\n"},
            }
        )
        self.assertEqual(action["type"], "tool")
        self.assertEqual(action["tool"], "write_file")
        self.assertEqual(action["args"]["path"], "app.py")

    def test_action_signature_is_stable(self) -> None:
        left = _action_signature(
            {"type": "tool", "tool": "read_file", "args": {"path": "app.py", "start_line": 1}}
        )
        right = _action_signature(
            {"tool": "read_file", "args": {"start_line": 1, "path": "app.py"}, "type": "tool"}
        )
        self.assertEqual(left, right)

    def test_write_file_rejects_placeholder_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ToolRunner(
                AgentConfig(
                    base_url="http://127.0.0.1:8000/v1",
                    model="test-model",
                    api_key=None,
                    cwd=Path(tmpdir).resolve(),
                )
            )
            result = runner.write_file("relative path", "hello")
            self.assertIn("placeholder value", result.output)
            self.assertFalse((Path(tmpdir) / "relative path").exists())

    def test_write_file_rejects_placeholder_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ToolRunner(
                AgentConfig(
                    base_url="http://127.0.0.1:8000/v1",
                    model="test-model",
                    api_key=None,
                    cwd=Path(tmpdir).resolve(),
                )
            )
            result = runner.write_file("app.py", "...full file contents...")
            self.assertIn("placeholder value", result.output)
            self.assertFalse((Path(tmpdir) / "app.py").exists())

    def test_write_file_reports_changed_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ToolRunner(
                AgentConfig(
                    base_url="http://127.0.0.1:8000/v1",
                    model="test-model",
                    api_key=None,
                    cwd=Path(tmpdir).resolve(),
                )
            )
            result = runner.write_file("app.py", "print('hi')\n")
            self.assertEqual(result.changed_paths, ("app.py",))


if __name__ == "__main__":
    unittest.main()
