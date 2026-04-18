# Self-Hosted Local AI Coding Agent

This repository gives you both halves of the stack:

- an Ubuntu-side inference server plan using `llama.cpp` and a small Qwen coder GGUF, powered by NVIDIA 2070 SUPER
- a macOS CLI agent that talks to that server over your LAN and can inspect files, edit code, and run shell commands with approval gates

## Recommended stack

### Server

- `llama.cpp` on Ubuntu
- Qwen `Qwen2.5-Coder-1.5B-Instruct-GGUF` as the starting model
- `systemd` to keep `llama-server` running on boot
- OpenAI-compatible HTTP API over your LAN

Why this stack:

- it serves GGUF directly
- it avoids extra orchestration layers
- it exposes a familiar `/v1/chat/completions` endpoint
- swapping to a stronger GGUF later does not require changing the client

Detailed server instructions are in [docs/ubuntu-inference-server.md](docs/ubuntu-inference-server.md).

### Client

- Python 3.11+
- standard-library `argparse`
- standard-library `urllib`
- a small explicit JSON tool loop instead of a heavyweight agent framework

Why this stack:

- file operations and shell execution are straightforward in Python
- the prompt and tool protocol stay short, which matters for a 1.5B model
- the permission model is easy to audit because the shell gate is local and explicit
- the CLI runs on a stock Python install without extra packages

## Architecture

```text
Mac project directory
  └─ agent "refactor my auth module"
        ├─ Python CLI
        │    ├─ reads/searches files inside the current workspace
        │    ├─ writes targeted edits
        │    ├─ asks before risky shell commands
        │    └─ sends compact context to the model server
        └─ HTTP over LAN
             └─ Ubuntu llama-server + Qwen GGUF
```

The CLI is intentionally conservative:

- file access is limited to the current project root
- read-only shell commands and common test/build commands are auto-approved
- risky or unknown shell commands require confirmation
- file deletion is not exposed as a first-class tool
- obvious placeholder arguments from the prompt schema are rejected instead of being executed or written

## Install the CLI on your Mac

From this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or with `uv`:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Configure the CLI

Set these environment variables on your Mac:

```bash
export LOCAL_AGENT_BASE_URL="http://SERVER_IP:8000/v1"
export LOCAL_AGENT_MODEL="qwen2.5-coder-1.5b-instruct-q4_k_m"
```

If you place a reverse proxy with auth in front of the server:

```bash
export LOCAL_AGENT_API_KEY="your-shared-token"
```

## Run it

Inside any project directory:

```bash
agent refactor my auth module
```

Other examples:

```bash
agent add tests for the token refresh flow
agent rename ConfigLoader to SettingsLoader and update imports
```

## Permission model

The shell safety gate is in [src/local_agent/safety.py](src/local_agent/safety.py).

Current behavior:

- auto-allow read-only commands like `ls`, `cat`, `rg`, `git status`, `git diff`
- auto-allow common `test`, `lint`, and `build` commands
- prompt before dangerous commands like `rm`, `mv`, `sudo`, `git reset`, and pipeline-heavy shell commands

This is intentionally stricter than your stated minimum. That is the right tradeoff for a first local agent because small local models are more error-prone than hosted frontier models.

## Important limitation

The architecture is sound, but the model size is the limiting factor.

A 1.5B Qwen coder will work for:

- small refactors
- guided file edits
- simple test-fix loops
- grep-driven codebase navigation

It will struggle with:

- large multi-file architectural changes
- ambiguous requests
- long context windows
- subtle bug hunts

If the agent workflow feels correct but the answers are weak, keep the same code and replace only the model on the Ubuntu server.

## Verify the scaffold

```bash
python3 -m unittest discover -s tests
python3 -m compileall src
```
