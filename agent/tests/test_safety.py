from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_agent.safety import classify_command


class SafetyTests(unittest.TestCase):
    def test_read_only_command_is_auto_allowed(self) -> None:
        decision = classify_command("rg AuthService src")
        self.assertFalse(decision.should_ask)

    def test_test_command_is_auto_allowed(self) -> None:
        decision = classify_command("pytest")
        self.assertFalse(decision.should_ask)

    def test_dangerous_command_requires_approval(self) -> None:
        decision = classify_command("rm -rf build")
        self.assertTrue(decision.should_ask)

    def test_pipeline_requires_approval(self) -> None:
        decision = classify_command("rg AuthService src | head")
        self.assertTrue(decision.should_ask)

    def test_placeholder_command_requires_approval(self) -> None:
        decision = classify_command("shell command")
        self.assertTrue(decision.should_ask)


if __name__ == "__main__":
    unittest.main()
