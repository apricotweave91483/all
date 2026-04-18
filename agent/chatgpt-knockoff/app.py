#!/usr/bin/env python3
import json
import os
import secrets
import threading
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request


HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "1234"))
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8000/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "").strip()
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    (
        "Your name is Chad Jippity. "
        "Prefer plain text over Markdown. "
        "Avoid Markdown formatting unless the user explicitly asks for it."
    ),
).strip()
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
MODEL_CACHE = {"name": MODEL_NAME}
MODEL_LOCK = threading.Lock()

HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>chad jippity</title>
</head>
<body>
  <h1>chad jippity</h1>
  <button id="reset">new chat / forget everything</button>
  <hr>
  <div id="messages"></div>
  <hr>
  <form id="chat-form">
    <textarea id="message" rows="8" cols="120" placeholder="type words here"></textarea>
    <br>
    <button type="submit">send</button>
  </form>
  <p id="status"></p>

  <script>
    const messagesEl = document.getElementById("messages");
    const formEl = document.getElementById("chat-form");
    const messageEl = document.getElementById("message");
    const statusEl = document.getElementById("status");
    const resetEl = document.getElementById("reset");

    function renderMessage(role, content) {
      const block = document.createElement("div");
      const title = document.createElement("h3");
      const body = document.createElement("pre");
      title.textContent = role === "assistant" ? "chad" : role;
      body.textContent = content;
      block.appendChild(title);
      block.appendChild(body);
      block.appendChild(document.createElement("hr"));
      messagesEl.appendChild(block);
    }

    function renderHistory(messages) {
      messagesEl.innerHTML = "";
      for (const msg of messages) {
        renderMessage(msg.role, msg.content);
      }
      window.scrollTo(0, document.body.scrollHeight);
    }

    async function loadHistory() {
      statusEl.textContent = "loading history...";
      const res = await fetch("/api/history");
      const data = await res.json();
      renderHistory(data.messages || []);
      statusEl.textContent = "";
    }

    formEl.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = messageEl.value.trim();
      if (!text) {
        return;
      }

      renderMessage("user", text);
      messageEl.value = "";
      statusEl.textContent = "waiting for model...";

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "request failed");
        }
        renderMessage("assistant", data.reply || "");
        statusEl.textContent = "";
      } catch (err) {
        renderMessage("error", String(err));
        statusEl.textContent = "request failed";
      }
    });

    resetEl.addEventListener("click", async () => {
      statusEl.textContent = "resetting...";
      const res = await fetch("/api/reset", { method: "POST" });
      const data = await res.json();
      renderHistory(data.messages || []);
      statusEl.textContent = "";
    });

    loadHistory().catch((err) => {
      statusEl.textContent = "failed to load history: " + String(err);
    });
  </script>
</body>
</html>
"""


def json_bytes(payload):
    return json.dumps(payload).encode("utf-8")


def guess_model_name():
    with MODEL_LOCK:
        if MODEL_CACHE["name"]:
            return MODEL_CACHE["name"]

        models_url = f"{LLM_BASE_URL}/models"
        req = request.Request(models_url, method="GET")
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        models = data.get("data") or []
        if not models:
            raise RuntimeError("No models returned by upstream /models endpoint")

        MODEL_CACHE["name"] = models[0]["id"]
        return MODEL_CACHE["name"]


def call_llm(messages):
    payload = {
        "model": guess_model_name(),
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }
    req = request.Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Upstream returned no choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("Upstream returned a non-text response")
    return content


class ChatHandler(BaseHTTPRequestHandler):
    server_version = "UglyChat/0.1"

    def do_GET(self):
        if self.path == "/":
            self._serve_index()
            return

        if self.path == "/api/history":
            session_id, is_new = self._get_or_create_session()
            messages = self._session_messages(session_id)
            self._send_json({"messages": messages}, set_cookie=is_new, session_id=session_id)
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path == "/api/chat":
            self._handle_chat()
            return

        if self.path == "/api/reset":
            session_id, is_new = self._get_or_create_session()
            with SESSIONS_LOCK:
                SESSIONS[session_id] = []
            self._send_json({"ok": True, "messages": []}, set_cookie=is_new, session_id=session_id)
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, fmt, *args):
        return

    def _serve_index(self):
        session_id, is_new = self._get_or_create_session()
        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if is_new:
            self.send_header("Set-Cookie", self._session_cookie_header(session_id))
        self.end_headers()
        self.wfile.write(body)

    def _handle_chat(self):
        session_id, is_new = self._get_or_create_session()
        payload = self._read_json_body()
        if payload is None:
            self._send_json(
                {"error": "invalid json body"},
                status=HTTPStatus.BAD_REQUEST,
                set_cookie=is_new,
                session_id=session_id,
            )
            return

        user_message = (payload.get("message") or "").strip()
        if not user_message:
            self._send_json(
                {"error": "message is required"},
                status=HTTPStatus.BAD_REQUEST,
                set_cookie=is_new,
                session_id=session_id,
            )
            return

        with SESSIONS_LOCK:
            history = list(SESSIONS.get(session_id, []))

        upstream_messages = []
        if SYSTEM_PROMPT:
            upstream_messages.append({"role": "system", "content": SYSTEM_PROMPT})
        upstream_messages.extend(history)
        upstream_messages.append({"role": "user", "content": user_message})

        try:
            reply = call_llm(upstream_messages)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self._send_json(
                {"error": f"upstream http error {exc.code}: {detail}"},
                status=HTTPStatus.BAD_GATEWAY,
                set_cookie=is_new,
                session_id=session_id,
            )
            return
        except Exception as exc:
            self._send_json(
                {"error": f"upstream request failed: {exc}"},
                status=HTTPStatus.BAD_GATEWAY,
                set_cookie=is_new,
                session_id=session_id,
            )
            return

        with SESSIONS_LOCK:
            session_messages = SESSIONS.setdefault(session_id, [])
            session_messages.append({"role": "user", "content": user_message})
            session_messages.append({"role": "assistant", "content": reply})

        self._send_json(
            {"reply": reply},
            set_cookie=is_new,
            session_id=session_id,
        )

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None

        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def _send_json(self, payload, status=HTTPStatus.OK, set_cookie=False, session_id=None):
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if set_cookie and session_id:
            self.send_header("Set-Cookie", self._session_cookie_header(session_id))
        self.end_headers()
        self.wfile.write(body)

    def _get_or_create_session(self):
        cookie_header = self.headers.get("Cookie", "")
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        morsel = cookies.get("session_id")
        if morsel and morsel.value:
            session_id = morsel.value
            with SESSIONS_LOCK:
                SESSIONS.setdefault(session_id, [])
            return session_id, False

        session_id = secrets.token_hex(16)
        with SESSIONS_LOCK:
            SESSIONS[session_id] = []
        return session_id, True

    def _session_cookie_header(self, session_id):
        return f"session_id={session_id}; Path=/; HttpOnly; SameSite=Lax"

    def _session_messages(self, session_id):
        with SESSIONS_LOCK:
            return list(SESSIONS.get(session_id, []))


def main():
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    print(f"Serving ugly chat on http://{HOST}:{PORT}")
    print(f"Proxying LLM requests to {LLM_BASE_URL}")
    if MODEL_NAME:
        print(f"Using configured model: {MODEL_NAME}")
    else:
        print("Model name not set; first request will auto-detect from /v1/models")
    server.serve_forever()


if __name__ == "__main__":
    main()
