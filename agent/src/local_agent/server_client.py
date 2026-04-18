from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import request
from urllib.error import HTTPError, URLError


@dataclass(slots=True)
class ModelClient:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: int = 120

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 900) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": False,
        }

        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Connection error: {exc.reason}") from exc

        message = data["choices"][0]["message"]["content"]
        if isinstance(message, list):
            return "".join(
                part.get("text", "") for part in message if isinstance(part, dict)
            )
        return str(message)
