# Ugly ChatGPT Knockoff

Minimal Python chat site that:

- serves an ugly HTML page on port `1234`
- keeps chat history in RAM per browser session
- sends the whole conversation to a local OpenAI-compatible `llama.cpp` server at `127.0.0.1:8000`

No external Python packages are required.

## Run

```bash
cd /path/to/chatgpt-knockoff-website-src
python3 app.py
```

Then open:

```text
http://SERVER_IP:1234
```

For your setup that would be:

```text
http://192.168.1.160:1234
```

## Config

Optional environment variables:

```bash
export HOST=0.0.0.0
export PORT=1234
export LLM_BASE_URL=http://127.0.0.1:8000/v1
export MODEL_NAME=""
export SYSTEM_PROMPT=""
export MAX_TOKENS=1024
export TEMPERATURE=0.7
python3 app.py
```

If `MODEL_NAME` is blank, the app asks `GET /v1/models` and uses the first returned model id.

## What It Does

- `GET /` serves the HTML page
- `GET /api/history` returns the current browser session's chat history
- `POST /api/chat` sends the full chat history plus the new user message upstream
- `POST /api/reset` clears the current browser session's chat

## Notes

- Memory is in RAM only. Restarting the Python process clears chats.
- Context grows forever until the model runs out of room. That is intentional here.
- Responses are not streamed. The page waits for the full reply.

## Example systemd unit

Save this as something like `/etc/systemd/system/ugly-chat.service`:

```ini
[Unit]
Description=Ugly ChatGPT Knockoff
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/youruser/chatgpt-knockoff-website-src
Environment=HOST=0.0.0.0
Environment=PORT=1234
Environment=LLM_BASE_URL=http://127.0.0.1:8000/v1
ExecStart=/usr/bin/python3 /home/youruser/chatgpt-knockoff-website-src/app.py
Restart=always
RestartSec=2
User=youruser

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ugly-chat.service
sudo systemctl status ugly-chat.service
```
