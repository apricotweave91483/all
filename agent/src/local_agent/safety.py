from __future__ import annotations

from dataclasses import dataclass
import shlex


READ_ONLY_COMMANDS = {
    "cat",
    "find",
    "git",
    "grep",
    "head",
    "less",
    "ls",
    "pwd",
    "rg",
    "sed",
    "stat",
    "tail",
    "tree",
    "wc",
    "which",
}

READ_ONLY_GIT_SUBCOMMANDS = {"diff", "log", "show", "status"}

SAFE_TASK_COMMANDS = {
    ("cargo", "build"),
    ("cargo", "check"),
    ("cargo", "clippy"),
    ("cargo", "test"),
    ("go", "build"),
    ("go", "test"),
    ("make",),
    ("npm", "run", "build"),
    ("npm", "run", "lint"),
    ("npm", "run", "test"),
    ("npm", "test"),
    ("pnpm", "build"),
    ("pnpm", "lint"),
    ("pnpm", "run", "build"),
    ("pnpm", "run", "lint"),
    ("pnpm", "run", "test"),
    ("pnpm", "test"),
    ("python", "-m", "pytest"),
    ("python3",),
    ("python3", "-m", "pytest"),
    ("pytest",),
    ("ruff", "check"),
    ("tsc",),
    ("uv", "run"),
    ("yarn", "build"),
    ("yarn", "lint"),
    ("yarn", "test"),
}

DANGEROUS_TOKENS = {
    "dd",
    "diskutil",
    "git-clean",
    "git-reset",
    "git-restore",
    "git-revert",
    "mkfs",
    "mv",
    "poweroff",
    "reboot",
    "rm",
    "shutdown",
    "sudo",
}

SHELL_OPERATORS = ("&&", "||", ";", "|", ">", ">>", "<", "$(", "`")


@dataclass(slots=True)
class SafetyDecision:
    should_ask: bool
    reason: str


def classify_command(command: str) -> SafetyDecision:
    stripped = command.strip()
    if not stripped:
        return SafetyDecision(True, "empty shell command")

    if stripped == "shell command":
        return SafetyDecision(True, "placeholder shell command was provided instead of a real command")

    if any(operator in stripped for operator in SHELL_OPERATORS):
        return SafetyDecision(
            True,
            "shell operators or pipelines are present, so the command needs review",
        )

    try:
        tokens = shlex.split(stripped)
    except ValueError:
        return SafetyDecision(True, "the shell command could not be parsed safely")

    if not tokens:
        return SafetyDecision(True, "empty shell command")

    if _is_dangerous(tokens):
        return SafetyDecision(
            True,
            "the command can delete, reset, or mutate state in a risky way",
        )

    if _is_read_only(tokens):
        return SafetyDecision(False, "read-only command")

    if _matches_safe_task(tokens):
        return SafetyDecision(False, "common test, lint, or build command")

    return SafetyDecision(
        True,
        "this command is not in the allowlist, so it needs explicit approval",
    )


def _is_read_only(tokens: list[str]) -> bool:
    command = tokens[0]
    if command == "git" and len(tokens) >= 2:
        return tokens[1] in READ_ONLY_GIT_SUBCOMMANDS
    return command in READ_ONLY_COMMANDS


def _matches_safe_task(tokens: list[str]) -> bool:
    for prefix in SAFE_TASK_COMMANDS:
        if tuple(tokens[: len(prefix)]) == prefix:
            return True
    return False


def _is_dangerous(tokens: list[str]) -> bool:
    command = tokens[0]
    if command in {"rm", "mv", "sudo", "dd", "diskutil", "mkfs", "reboot", "shutdown", "poweroff"}:
        return True
    if command == "git" and len(tokens) >= 2:
        joined = f"git-{tokens[1]}"
        return joined in DANGEROUS_TOKENS
    return False
