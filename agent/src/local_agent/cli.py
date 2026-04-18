from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

from .config import AgentConfig
from .server_client import ModelClient
from .tools import ToolRunner

KNOWN_TOOL_NAMES = {
    "list_dir",
    "read_file",
    "search",
    "write_file",
    "replace_in_file",
    "run_shell",
}
READ_ONLY_TOOLS = {"list_dir", "read_file", "search"}
MAX_NO_PROGRESS_STEPS = 4
MAX_REPEATED_FINALS = 2
MAX_REPEATED_IDENTICAL_ACTIONS = 3

SYSTEM_PROMPT = """You are a local coding agent operating inside one project directory.

Your job is to solve the user's coding task by using tools.

Rules:
- Stay inside the workspace root.
- Prefer inspecting files before editing them.
- Use write_file for full rewrites and replace_in_file for focused edits.
- Use run_shell for tests, builds, or commands the file tools cannot do.
- Do not ask the human questions unless you are blocked by missing approval or missing information.
- Reply with JSON only. No markdown. No code fences.
- Never copy placeholder text from the tool schema. Do not output values like "relative path", "shell command", or "...full file contents...".
- When you use write_file, provide the exact final contents of the real target file.
- Use the exact wrapper for tool calls: type must be "tool" and the tool name must go in the "tool" field.
- Do not use shorthand like {"type":"write_file", ...}. That shorthand is invalid.
- Do not modify files unless the goal requires a code or file change.
- For verification, inspection, explanation, or read-only tasks, prefer read-only tools and finish once you have the result.
- When a task only requires checking or reporting something, you may return final without changing files.
- For edit tasks, do not return final until a write tool has succeeded and you have checked the result with read_file, list_dir, or a safe shell command when appropriate.
- Never claim that you created or updated a file unless a write tool actually succeeded for that file.

Valid JSON shapes:
{"type":"tool","tool":"list_dir","args":{"path":".","recursive":false}}
{"type":"tool","tool":"read_file","args":{"path":"src/app.py","start_line":1,"end_line":200}}
{"type":"tool","tool":"search","args":{"pattern":"AuthService","path":"src"}}
{"type":"tool","tool":"write_file","args":{"path":"src/app.py","content":"...full file contents..."}}
{"type":"tool","tool":"replace_in_file","args":{"path":"src/app.py","old":"before","new":"after","count":1}}
{"type":"tool","tool":"run_shell","args":{"command":"pytest","timeout_seconds":180}}
{"type":"final","summary":"brief summary for the user"}
{"type":"final","summary":"brief summary for the user","no_changes_needed":true}

If a tool fails, adapt and keep going.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent",
        description="Local coding agent that talks to a self-hosted OpenAI-compatible model server.",
    )
    parser.add_argument("goal", nargs="+", help="Natural-language goal for the agent.")
    parser.add_argument("--base-url", help="OpenAI-compatible server base URL.")
    parser.add_argument("--model", help="Model name exposed by the server.")
    parser.add_argument("--max-iterations", type=int, help="Maximum agent steps.")
    parser.add_argument(
        "--auto-approve-risky-shell",
        action="store_true",
        help="Skip confirmation prompts for non-allowlisted shell commands.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cwd = Path.cwd()
    config = AgentConfig.from_env(cwd)

    if args.base_url:
        config.base_url = args.base_url.rstrip("/")
        if not config.base_url.endswith("/v1"):
            config.base_url = f"{config.base_url}/v1"
    if args.model:
        config.model = args.model
    if args.max_iterations is not None:
        config.max_iterations = args.max_iterations
    if args.auto_approve_risky_shell:
        config.auto_approve_risky_shell = True

    tools = ToolRunner(config=config)
    client = ModelClient(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
    )

    user_goal = " ".join(args.goal).strip()
    requires_workspace_changes = _goal_requires_workspace_changes(user_goal)
    print(f"Goal: {user_goal}")
    print(f"Workspace: {config.cwd}")
    print(f"Model: {config.model} @ {config.base_url}")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Workspace root: {config.cwd}\n"
                f"Top-level tree:\n{tools.describe_workspace()}\n\n"
                f"Tool reference:\n{tools.schema_text()}\n\n"
                f"Goal: {user_goal}"
            ),
        },
    ]
    changed_paths: set[str] = set()
    no_progress_steps = 0
    repeated_finals_without_changes = 0
    last_action_signature: str | None = None
    repeated_identical_actions = 0

    for step in range(1, config.max_iterations + 1):
        print(f"Step {step}")
        try:
            response_text = client.chat(messages)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"Model request failed: {exc}") from exc

        try:
            action = _normalize_action(_extract_json(response_text))
        except ValueError:
            messages.append({"role": "assistant", "content": response_text})
            messages.append(
                {
                    "role": "user",
                    "content": "Your last response was invalid. Reply with a single JSON object only.",
                }
            )
            print("Model returned invalid JSON; retrying.")
            continue

        action_signature = _action_signature(action)
        if action_signature == last_action_signature:
            repeated_identical_actions += 1
        else:
            repeated_identical_actions = 1
            last_action_signature = action_signature

        messages.append({"role": "assistant", "content": json.dumps(action)})

        if action.get("type") == "final":
            no_changes_needed = bool(action.get("no_changes_needed", False))
            if requires_workspace_changes and not changed_paths:
                repeated_finals_without_changes += 1
                no_progress_steps += 1
                if repeated_finals_without_changes >= MAX_REPEATED_FINALS:
                    print("Stopped early: repeated finish attempts without any file changes.")
                    return 1
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You tried to finish without making any workspace changes. "
                            "This goal requires creating or modifying files, so do not claim success "
                            "until you have changed the required files and checked the result."
                        ),
                    }
                )
                continue
            repeated_finals_without_changes = 0
            summary = str(action.get("summary", "")).strip() or "Completed."
            if changed_paths:
                print(f"Changed files: {', '.join(sorted(changed_paths))}")
            print(summary)
            return 0

        if action.get("type") != "tool":
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Unknown action type. Use either type=tool or type=final. "
                        "For tool calls, the JSON must look like "
                        '{"type":"tool","tool":"write_file","args":{...}}.'
                    ),
                }
            )
            print(f"Unsupported action: {json.dumps(action)}")
            no_progress_steps += 1
            if no_progress_steps >= MAX_NO_PROGRESS_STEPS:
                print("Stopped early: unsupported or no-progress responses kept repeating.")
                return 1
            continue

        tool_name = action.get("tool")
        tool_args = action.get("args") or {}
        print(f"Tool: {tool_name}")
        changed_before = set(changed_paths)
        try:
            result = tools.run(str(tool_name), dict(tool_args))
        except Exception as exc:  # noqa: BLE001
            result = None
            tool_output = f"Tool error: {exc}"
        else:
            tool_output = result.output
            changed_paths.update(result.changed_paths)

        print("Tool completed.")
        if changed_paths == changed_before:
            no_progress_steps += 1
        else:
            no_progress_steps = 0
            repeated_finals_without_changes = 0

        if (
            tool_name in READ_ONLY_TOOLS
            and repeated_identical_actions >= MAX_REPEATED_IDENTICAL_ACTIONS
            and changed_paths == changed_before
        ):
            print("Stopped early: repeated identical read-only actions without progress.")
            return 1

        if no_progress_steps >= MAX_NO_PROGRESS_STEPS:
            print("Stopped early: no progress after repeated read-only or failed actions.")
            return 1

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Tool result for {tool_name}:\n{tool_output}\n\n"
                    "Continue working. Reply with JSON only."
                ),
            }
        )

    print("Stopped after reaching the iteration limit. The model needs more steps or a larger model.")
    return 1


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError("No JSON object found.")


def _normalize_action(action: dict) -> dict:
    action_type = action.get("type")
    if action_type in KNOWN_TOOL_NAMES and "tool" not in action:
        return {
            "type": "tool",
            "tool": action_type,
            "args": dict(action.get("args") or {}),
        }
    return action


def _action_signature(action: dict) -> str:
    return json.dumps(action, sort_keys=True)


def _goal_requires_workspace_changes(goal: str) -> bool:
    lowered = goal.lower()

    write_verbs = (
        "add ",
        "build ",
        "change ",
        "create ",
        "edit ",
        "fix ",
        "implement ",
        "make ",
        "modify ",
        "refactor ",
        "rename ",
        "rewrite ",
        "update ",
        "write ",
    )
    read_only_signals = (
        "check ",
        "explain ",
        "inspect ",
        "list ",
        "read ",
        "review ",
        "show ",
        "summarize ",
        "syntax error",
        "verify ",
        "what ",
        "why ",
    )

    if any(token in lowered for token in read_only_signals) and not any(
        token in lowered for token in write_verbs
    ):
        return False

    return any(token in lowered for token in write_verbs)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
