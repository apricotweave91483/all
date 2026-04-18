# Ubuntu LAN Inference Server

This setup uses `llama.cpp` because it serves GGUF models directly and exposes an OpenAI-compatible HTTP API. That keeps the client simple on macOS: it can talk to the server with the same `/v1/chat/completions` shape many SDKs already use.

## What to run

The instructions below assume:

- Ubuntu Server on a machine in your LAN
- a Qwen coder GGUF around 1.5B params
- port `8000`
- a dedicated service user named `llm`

## 1. Install system packages

```bash
sudo apt update
sudo apt install -y build-essential cmake git python3 python3-pip
```

If the server has an NVIDIA GPU, install the NVIDIA driver and CUDA toolkit first, then build `llama.cpp` with CUDA enabled. If it is CPU-only, skip the CUDA flag later.

## 2. Create a service user and directories

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin llm
sudo mkdir -p /opt/llama.cpp /opt/models /var/cache/llama.cpp
sudo chown -R llm:llm /opt/llama.cpp /opt/models /var/cache/llama.cpp
```

## 3. Build `llama.cpp`

`llama.cpp` documents `llama-server` as the OpenAI-compatible API server. Clone it and build it:

```bash
cd /opt
sudo git clone https://github.com/ggml-org/llama.cpp.git
sudo chown -R llm:llm /opt/llama.cpp
cd /opt/llama.cpp
```

CPU-only build:

```bash
sudo -u llm cmake -B build
sudo -u llm cmake --build build -j
```

NVIDIA build:

```bash
sudo -u llm cmake -B build -DGGML_CUDA=ON
sudo -u llm cmake --build build -j
```

## 4. Download the model

The official Qwen GGUF card shows a direct `huggingface-cli download` example for `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`. Install the CLI and download that file:

```bash
python3 -m pip install --upgrade huggingface_hub
sudo -u llm huggingface-cli download \
  Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF \
  qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --local-dir /opt/models \
  --local-dir-use-symlinks False
```

That quant is roughly 1.1 GB. It is a good starting point for CPU-only or modest GPU hardware. If code quality is too weak, move up to the 7B family later.

## 5. Test the server manually

CPU-only:

```bash
/opt/llama.cpp/build/bin/llama-server \
  -m /opt/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8000 \
  -c 8192
```

With NVIDIA acceleration, add `-ngl 99` to offload layers to the GPU:

```bash
/opt/llama.cpp/build/bin/llama-server \
  -m /opt/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8000 \
  -c 8192 \
  -ngl 99
```

From another machine on your LAN, verify the API:

```bash
curl http://SERVER_IP:8000/health
curl http://SERVER_IP:8000/v1/models
```

## 6. Install the systemd unit

Copy [`deploy/llama-server.service.example`](../deploy/llama-server.service.example) to `/etc/systemd/system/llama-server.service` and adjust:

- the model path
- `-ngl 99` if you are CPU-only
- the service user if you chose a different account

Then enable it:

```bash
sudo cp deploy/llama-server.service.example /etc/systemd/system/llama-server.service
sudo systemctl daemon-reload
sudo systemctl enable --now llama-server
sudo systemctl status llama-server
```

Useful service commands:

```bash
sudo journalctl -u llama-server -f
sudo systemctl restart llama-server
```

## 7. Restrict it to your LAN

If you use UFW, only allow your subnet:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp
```

If you need authentication, put Caddy or Nginx in front of `llama-server` and enforce a shared API key there. For a trusted home LAN, subnet restriction is often enough.

## Notes on sizing

- A 1.5B coder is enough for small edits, grep-driven refactors, and simple test-fix loops.
- It is not Codex-class. Expect it to need tighter prompts and more retries on larger codebases.
- If the workflow is good but quality is weak, the fastest upgrade path is keeping this exact architecture and swapping the model for a stronger GGUF later.
