# 🚀 Local & Cloud LLM Stack (Docker + Ollama + Open WebUI + PostgreSQL)

This repository provides an automated, hardware-aware stack for hosting a local Large Language Model (LLM) server and web interface. It includes user authentication, chat persistence, and automated optimization based on system specifications.

## Architecture

The stack consists of four core components:
1. **Ollama**: Serves open-source LLMs (Llama 3, DeepSeek-R1, Qwen, Gemma, etc.) with hardware-accelerated inference.
2. **Open WebUI**: A feature-rich browser client that mirrors the ChatGPT interface, with built-in user management, settings, and conversation memory.
3. **PostgreSQL**: A resilient, dedicated database for storing Open WebUI conversation logs, settings, and user accounts.
4. **OpenClaw**: An open-source autonomous AI agent gateway that connects your local LLMs to system tools (filesystem, terminal, web search) and communication channels.

```
       [ Browser Client ]
               │ (Port 8080)
               ▼
      [ Open WebUI Client ] ──(Save Chats)──► [ PostgreSQL Database ]
               │
               ▼ (Port 11434)
         [ Ollama API ] ◄────(Query Models)──── [ OpenClaw Gateway ] (Port 18789)
  (Linux/GPU Docker OR macOS Native)                │
                                                    ▼
                                     [ Local Files / Terminal / Web Tools ]
```

---

## Hardware-Aware Model Constraints

LLMs are resource-intensive. Running a model that exceeds system capacity leads to CPU thrift, thrashing, Out-of-Memory (OOM) crashes, or extremely sluggish output (less than 1 token/sec). 

Our interactive installer auto-detects:
- Available **System RAM**
- **CPU Cores** & Brand
- **GPU hardware** and dedicated **VRAM** (NVIDIA CUDA or Apple Silicon Unified Memory)

Models are dynamically categorized and recommended based on specs:
*   **Tiny (< 4GB RAM/VRAM)**: Qwen 2.5 1.5B, DeepSeek-R1 1.5B. Runs on low-spec VMs and entry-level laptops.
*   **Medium (4GB - 12GB RAM/VRAM)**: Llama 3.2 3B, Llama 3.1 8B, DeepSeek-R1 8B, Gemma 2 9B. Best for standard developer machines with 16GB RAM.
*   **Large (12GB - 24GB RAM/VRAM)**: Qwen 2.5 14B, DeepSeek-R1 14B. Good for machines with 24GB-32GB RAM or 12GB+ GPU VRAM.
*   **Extra Large (24GB - 48GB RAM/VRAM)**: DeepSeek-R1 32B. Requires high-spec workstation GPUs or Mac Studio.
*   **Enterprise (> 48GB RAM/VRAM)**: DeepSeek-R1 70B, Llama 3 70B. Requires multiple GPUs or 96GB+ Mac.

---

## macOS Apple Silicon Optimization

Docker Desktop on macOS cannot pass host Apple Silicon GPU resources (Metal) into containerized services. Running Ollama inside a Docker container on Mac forces it onto CPU, resulting in a 10x performance penalty.

**Our Installer Solution**:
When macOS is detected, you will be prompted to choose:
1.  **Native Host Ollama (Recommended)**: Runs Ollama as a native Mac app (utilizing full Metal GPU speed). The Open WebUI client runs in Docker and connects directly to the native host's API endpoint.
2.  **Containerized (CPU-only)**: Runs Ollama inside Docker on CPU (slow, but fully containerized).

---

## Getting Started

### Prerequisites

Ensure you have the following installed:
- [Docker](https://docs.docker.com/get-docker/) (Ensure Docker daemon is running)
- Python 3.x (to run the setup script)

### Setup & Launch

1. Clone or copy this repository to your host or cloud VM.
2. Execute the interactive installer:
   ```bash
   chmod +x setup.py
   python3 setup.py
   ```
3. Follow the prompts to:
   - Verify hardware specs.
   - Select recommended models.
   - Automatically configure environment variables and compose files.
   - Boot container services and auto-pull selected models.

### Accessing the Clients

- **Open WebUI**: [http://localhost:8080](http://localhost:8080)
- **OpenClaw Dashboard**: [http://localhost:18789](http://localhost:18789) (Securely bound to localhost. Access using the `OPENCLAW_GATEWAY_TOKEN` found in your generated `.env` file).
- **Ollama API**: [http://localhost:11434](http://localhost:11434)

#### Connecting OpenClaw to your local LLMs:
1. Open the **OpenClaw Dashboard** at `http://localhost:18789` and log in using your gateway token.
2. Go to **LLM Providers** and add a custom OpenAI-compatible provider:
   - **Provider URL**: `http://ollama:11434/v1` (if running Ollama in Docker) or `http://host.docker.internal:11434/v1` (if running native Ollama on macOS).
   - **API Key**: Any string (e.g., `ollama`).
3. Select your model (e.g., `deepseek-r1:14b` or `qwen2.5:14b`) to start executing tasks.

*Note: The first user to register on Open WebUI [http://localhost:8080](http://localhost:8080) will automatically be granted Owner/Administrator privileges. From there, you can enable/disable user registrations under Admin settings.*

---

## CLI & Manual Commands

If you prefer to manage the services or pull models manually:

### Updating & Patching the Stack
To automatically pull the latest git repository updates, download the newest Docker image updates (for Open WebUI, OpenClaw, PostgreSQL, and Ollama), and restart all services:
```bash
chmod +x update.sh
./update.sh
```

### Manage Docker Containers
```bash
# Start services (after running setup.py)
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f
```

### Pulling Models Manually
If running Ollama in Docker:
```bash
docker exec -it ollama-server ollama pull deepseek-r1:8b
```
If running Ollama natively on macOS:
```bash
ollama pull deepseek-r1:8b
```
