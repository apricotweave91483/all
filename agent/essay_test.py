#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from urllib import request


def main() -> int:
    base_url = os.environ.get("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
    model = os.environ.get("LOCAL_LLM_MODEL", "qwen2.5-coder-1.5b-instruct-q4_k_m")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Write a short essay about Mozart in 3 concise paragraphs.",
            }
        ],
        "temperature": 0.7,
        "max_tokens": 400,
        "stream": False,
    }

    req = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=120) as response:
        body = json.loads(response.read().decode("utf-8"))

    text = body["choices"][0]["message"]["content"]
    if isinstance(text, list):
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))

    sys.stdout.write(str(text).strip() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
