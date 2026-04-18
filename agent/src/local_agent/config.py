from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _normalize_base_url(value: str) -> str:
    value = value.rstrip("/")
    if value.endswith("/v1"):
        return value
    return f"{value}/v1"


@dataclass(slots=True)
class AgentConfig:
    base_url: str
    model: str
    api_key: str | None
    cwd: Path
    max_iterations: int = 16
    max_read_lines: int = 250
    max_tool_output_chars: int = 12000
    shell_timeout_seconds: int = 180
    auto_approve_risky_shell: bool = False

    @classmethod
    def from_env(cls, cwd: Path) -> "AgentConfig":
        base_url = _normalize_base_url(
            os.environ.get("LOCAL_AGENT_BASE_URL", "http://127.0.0.1:8000/v1")
        )
        return cls(
            base_url=base_url,
            model=os.environ.get(
                "LOCAL_AGENT_MODEL", "qwen2.5-coder-1.5b-instruct-q4_k_m"
            ),
            api_key=os.environ.get("LOCAL_AGENT_API_KEY"),
            cwd=cwd.resolve(),
            max_iterations=int(os.environ.get("LOCAL_AGENT_MAX_ITERATIONS", "16")),
            max_read_lines=int(os.environ.get("LOCAL_AGENT_MAX_READ_LINES", "250")),
            max_tool_output_chars=int(
                os.environ.get("LOCAL_AGENT_MAX_TOOL_OUTPUT_CHARS", "12000")
            ),
            shell_timeout_seconds=int(
                os.environ.get("LOCAL_AGENT_SHELL_TIMEOUT_SECONDS", "180")
            ),
            auto_approve_risky_shell=os.environ.get(
                "LOCAL_AGENT_AUTO_APPROVE_RISKY_SHELL", "0"
            ).lower()
            in {"1", "true", "yes"},
        )
