#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import json
import time
import shutil
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Optional

# Color codes for premium CLI styling
class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GRAY = '\033[90m'

# List of models with metadata
# RAM/VRAM recommendations are based on Q4_K_M quantizations
MODEL_CATALOG = [
    {
        "id": "deepseek-r1:1.5b",
        "name": "DeepSeek-R1 (1.5B)",
        "size_gb": 1.1,
        "min_ram_gb": 3,
        "recommend_gpu_vram_gb": 2,
        "description": "State-of-the-art reasoning model. Ultra-fast, ideal for low-spec hosts.",
        "category": "Tiny"
    },
    {
        "id": "qwen2.5:1.5b",
        "name": "Qwen 2.5 (1.5B)",
        "size_gb": 0.9,
        "min_ram_gb": 3,
        "recommend_gpu_vram_gb": 2,
        "description": "Highly capable lightweight general-purpose model.",
        "category": "Tiny"
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 (3B)",
        "size_gb": 2.0,
        "min_ram_gb": 6,
        "recommend_gpu_vram_gb": 4,
        "description": "Meta's lightweight model. Excellent balance of speed and logic.",
        "category": "Medium"
    },
    {
        "id": "deepseek-r1:8b",
        "name": "DeepSeek-R1 (8B)",
        "size_gb": 4.7,
        "min_ram_gb": 12,
        "recommend_gpu_vram_gb": 8,
        "description": "Meta Llama 8B distilled DeepSeek-R1 reasoning model. Recommended standard.",
        "category": "Medium"
    },
    {
        "id": "llama3.1:8b",
        "name": "Llama 3.1 (8B)",
        "size_gb": 4.7,
        "min_ram_gb": 12,
        "recommend_gpu_vram_gb": 8,
        "description": "Meta's standard 8B model. Great general-purpose chatbot capabilities.",
        "category": "Medium"
    },
    {
        "id": "gemma2:9b",
        "name": "Gemma 2 (9B)",
        "size_gb": 5.5,
        "min_ram_gb": 14,
        "recommend_gpu_vram_gb": 8,
        "description": "Google's open weights model. Excellent styling and instruction adherence.",
        "category": "Medium"
    },
    {
        "id": "deepseek-r1:14b",
        "name": "DeepSeek-R1 (14B)",
        "size_gb": 9.0,
        "min_ram_gb": 20,
        "recommend_gpu_vram_gb": 12,
        "description": "Qwen 14B distilled reasoning model. Great balance of reasoning depth and speed.",
        "category": "Large"
    },
    {
        "id": "qwen2.5:14b",
        "name": "Qwen 2.5 (14B)",
        "size_gb": 9.0,
        "min_ram_gb": 20,
        "recommend_gpu_vram_gb": 12,
        "description": "Highly capable coding and multilingual generalist model.",
        "category": "Large"
    },
    {
        "id": "deepseek-r1:32b",
        "name": "DeepSeek-R1 (32B)",
        "size_gb": 20.0,
        "min_ram_gb": 48,
        "recommend_gpu_vram_gb": 24,
        "description": "DeepSeek-R1 distilled from Qwen 32B. Very advanced reasoning capability.",
        "category": "Extra Large"
    },
    {
        "id": "deepseek-r1:70b",
        "name": "DeepSeek-R1 (70B)",
        "size_gb": 42.0,
        "min_ram_gb": 96,
        "recommend_gpu_vram_gb": 48,
        "description": "Llama 70B distilled reasoning model. Near-frontier grade performance.",
        "category": "Enterprise"
    }
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(f"{Color.CYAN}{Color.BOLD}")
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│             🚀  DOCKER LLM STACK INSTALLER                  │")
    print("│         Ollama  •  Open WebUI  •  PostgreSQL DB             │")
    print("└─────────────────────────────────────────────────────────────┘")
    print(f"{Color.ENDC}")

def get_ram_info() -> Tuple[float, str]:
    """Detects total system RAM in GB and returns a descriptive string."""
    sys_type = platform.system()
    if sys_type == "Darwin":
        try:
            res = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True, check=True)
            bytes_val = int(res.stdout.strip())
            gb_val = bytes_val / (1024 ** 3)
            return gb_val, f"{gb_val:.2f} GB (macOS Unified Memory)"
        except Exception:
            return 8.0, "8.0 GB (Fallback)"
    elif sys_type == "Linux":
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        parts = line.split()
                        kb_val = int(parts[1])
                        gb_val = kb_val / (1024 ** 2)
                        return gb_val, f"{gb_val:.2f} GB"
        except Exception:
            pass
    return 8.0, "8.0 GB (Fallback)"

def get_cpu_info() -> Tuple[int, str]:
    """Detects CPU core count and brand string."""
    cores = os.cpu_count() or 1
    sys_type = platform.system()
    brand = "Unknown CPU"
    if sys_type == "Darwin":
        try:
            res = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True, check=True)
            brand = res.stdout.strip()
        except Exception:
            brand = "Apple Silicon" if platform.processor() == "arm" else "Intel Core"
    elif sys_type == "Linux":
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        brand = line.split(':', 1)[1].strip()
                        break
        except Exception:
            brand = "Linux CPU"
    return cores, f"{brand} ({cores} Cores)"

def get_gpu_info() -> Tuple[Optional[str], float]:
    """Detects GPU type (NVIDIA/Apple Silicon) and total VRAM in GB."""
    sys_type = platform.system()
    if sys_type == "Darwin":
        # Apple Silicon Mac uses Unified Memory
        cores, brand = get_cpu_info()
        if "Apple" in brand:
            ram_gb, _ = get_ram_info()
            # Apple Silicon allocates up to 70% or 75% of unified memory for GPU
            gpu_vram = ram_gb * 0.70 
            return f"{brand} Integrated GPU", gpu_vram
        return None, 0.0
    
    # Check for nvidia-smi
    nvidia_smi = shutil.which('nvidia-smi')
    if nvidia_smi:
        try:
            res = subprocess.run(
                [nvidia_smi, '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, check=True
            )
            out = res.stdout.strip().split(',')
            if len(out) >= 2:
                gpu_name = out[0].strip()
                vram_mb = int(out[1].strip())
                return gpu_name, vram_mb / 1024.0
        except Exception:
            pass
    return None, 0.0

def detect_hardware() -> Dict:
    print(f"{Color.CYAN}🔎 Scanning system hardware configuration...{Color.ENDC}")
    ram_gb, ram_str = get_ram_info()
    cpu_cores, cpu_str = get_cpu_info()
    gpu_name, gpu_vram = get_gpu_info()
    
    # Classify System tier
    # Standard metrics for model loading:
    # Large reasoning models need high specs
    system_tier = "Entry Level"
    max_recommended_model_size_gb = 2.0
    
    available_resource_gb = gpu_vram if gpu_vram > 0 else ram_gb
    
    if available_resource_gb >= 40:
        system_tier = "Enterprise / Multi-GPU"
        max_recommended_model_size_gb = 45.0
    elif available_resource_gb >= 22:
        system_tier = "High-End Creator / Pro GPU"
        max_recommended_model_size_gb = 22.0
    elif available_resource_gb >= 12:
        system_tier = "Mid-High Performance"
        max_recommended_model_size_gb = 10.0
    elif available_resource_gb >= 7:
        system_tier = "Standard Desktop / VM"
        max_recommended_model_size_gb = 5.0
    else:
        system_tier = "Entry Level / CPU-Only VM"
        max_recommended_model_size_gb = 2.2
        
    return {
        "os": platform.system(),
        "ram_gb": ram_gb,
        "ram_str": ram_str,
        "cpu_cores": cpu_cores,
        "cpu_str": cpu_str,
        "gpu_name": gpu_name,
        "gpu_vram_gb": gpu_vram,
        "tier": system_tier,
        "max_recommended_model_size_gb": max_recommended_model_size_gb
    }

def print_hardware_report(hw: Dict):
    print(f"\n{Color.BOLD}--- Hardware Discovery Report ---{Color.ENDC}")
    print(f"🖥️  {Color.BOLD}OS:{Color.ENDC} {hw['os']}")
    print(f"💿 {Color.BOLD}Processor:{Color.ENDC} {hw['cpu_str']}")
    print(f"🧠 {Color.BOLD}System RAM:{Color.ENDC} {hw['ram_str']}")
    if hw['gpu_name']:
        print(f"🎮 {Color.BOLD}GPU detected:{Color.ENDC} {hw['gpu_name']} ({hw['gpu_vram_gb']:.2f} GB VRAM)")
    else:
        print(f"🎮 {Color.BOLD}GPU detected:{Color.ENDC} {Color.WARNING}None (Running CPU-only mode for Ollama in Docker){Color.ENDC}")
    
    print(f"🏷️  {Color.BOLD}Hardware Class:{Color.ENDC} {Color.GREEN}{hw['tier']}{Color.ENDC}")
    print(f"📦 {Color.BOLD}Max Recommended Model Size:{Color.ENDC} {Color.CYAN}~{hw['max_recommended_model_size_gb']} GB{Color.ENDC}")
    print(f"---------------------------------\n")

def check_dependencies() -> bool:
    print(f"{Color.CYAN}🔎 Verification: Checking for Docker & Docker Compose...{Color.ENDC}")
    docker = shutil.which('docker')
    if not docker:
        print(f"{Color.FAIL}❌ Docker is not installed on this system.{Color.ENDC}")
        print("Please install Docker first: https://docs.docker.com/get-docker/")
        return False
        
    # Check docker compose compatibility
    try:
        res = subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Docker Compose command available: {res.stdout.strip()}")
            return True
    except Exception:
        pass
        
    try:
        res = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ docker-compose legacy command available: {res.stdout.strip()}")
            return True
    except Exception:
        pass
        
    print(f"{Color.FAIL}❌ Docker Compose is not installed.{Color.ENDC}")
    print("Please install the Docker Compose plugin or CLI.")
    return False

def setup_mac_options(hw: Dict) -> str:
    """Returns 'native' or 'docker' for macOS configuration."""
    print(f"{Color.WARNING}🍎 Apple macOS detected.{Color.ENDC}")
    print("Docker Desktop on macOS cannot access Apple Silicon GPUs (Metal).")
    print("Running Ollama inside Docker will default to CPU execution (extremely slow).")
    print(f"\nChoose your Ollama backend strategy:")
    print(f"  {Color.GREEN}1) [RECOMMENDED] Native Host Ollama{Color.ENDC}")
    print("     - Run Ollama as a native macOS application (utilizes fast Apple GPU acceleration).")
    print("     - Open WebUI and PostgreSQL will run in Docker and connect to the host Ollama API.")
    print("  2) Fully Containerized (CPU only)")
    print("     - Run everything (including Ollama) in Docker containers.")
    print("     - Very slow generation speeds. Useful if you cannot install native Ollama.")
    
    while True:
        choice = input(f"\nSelect setup strategy (1 or 2): ").strip()
        if choice in ('1', 'native'):
            return "native"
        elif choice == '2':
            return "docker"
        else:
            print(f"{Color.FAIL}Invalid option. Enter 1 or 2.{Color.ENDC}")

def select_models(hw: Dict) -> List[str]:
    print(f"{Color.BOLD}🤖 LLM Model Selection Catalog{Color.ENDC}")
    print(f"Select models to automatically pull during setup.")
    print(f"Models are dynamically constrained by your hardware profile.\n")
    
    choices = []
    
    max_rec = hw['max_recommended_model_size_gb']
    
    # Print table header
    print(f"{'#':<3} | {'Model ID':<20} | {'Size':<8} | {'Min RAM':<8} | {'Status/Recommendation':<25}")
    print("-" * 75)
    
    for idx, model in enumerate(MODEL_CATALOG, 1):
        fit_status = ""
        is_recommended = False
        
        # Check constraints
        if model['size_gb'] > max_rec:
            fit_status = f"{Color.WARNING}⚠️  Oversized (May run slowly / OOM){Color.ENDC}"
        else:
            # Recommend the best matching models in their category
            # If system has enough ram, recommend standard 8b.
            # If system is entry level, recommend 1.5b/3b.
            if hw['ram_gb'] < 8.0 and model['category'] == 'Tiny':
                fit_status = f"{Color.GREEN}⭐ Recommended for your system{Color.ENDC}"
                is_recommended = True
            elif 8.0 <= hw['ram_gb'] < 16.0 and model['id'] in ('llama3.2:3b', 'deepseek-r1:8b'):
                fit_status = f"{Color.GREEN}⭐ Recommended standard{Color.ENDC}"
                is_recommended = True
            elif hw['ram_gb'] >= 16.0 and model['id'] in ('deepseek-r1:8b', 'deepseek-r1:14b'):
                fit_status = f"{Color.GREEN}⭐ Recommended performance{Color.ENDC}"
                is_recommended = True
            else:
                fit_status = f"{Color.BLUE}Fits Specs{Color.ENDC}"
                
        rec_label = f"[{model['category']}]"
        print(f"{idx:<3} | {Color.BOLD}{model['name']:<20}{Color.ENDC} | {model['size_gb']:>5.1f} GB | {model['min_ram_gb']:>5} GB | {fit_status:<25}")
        print(f"    {Color.GRAY}{model['description']}{Color.ENDC}\n")
        
    print(f"Enter numbers of models to select (separated by commas, e.g., '1,4' or '4').")
    print(f"Leave empty to skip model auto-pull and configure manually later.")
    
    while True:
        try:
            val = input(f"\nSelect models: ").strip()
            if not val:
                return []
            indices = [int(i.strip()) for i in val.split(',')]
            valid = True
            selected_ids = []
            
            for idx in indices:
                if idx < 1 or idx > len(MODEL_CATALOG):
                    print(f"{Color.FAIL}Index {idx} is out of bounds.{Color.ENDC}")
                    valid = False
                    break
                
                chosen_model = MODEL_CATALOG[idx - 1]
                # If chosen model is oversized, confirm with user
                if chosen_model['size_gb'] > max_rec:
                    print(f"\n{Color.WARNING}⚠️  Warning: {chosen_model['name']} requires {chosen_model['min_ram_gb']}GB RAM.")
                    print(f"Your hardware profile may experience out-of-memory errors or extremely slow execution.{Color.ENDC}")
                    confirm = input("Are you sure you want to select this model anyway? (y/n): ").strip().lower()
                    if confirm != 'y':
                        valid = False
                        break
                        
                selected_ids.append(chosen_model['id'])
                
            if valid:
                return selected_ids
        except ValueError:
            print(f"{Color.FAIL}Please enter valid numbers separated by commas.{Color.ENDC}")

def read_existing_env() -> Dict[str, str]:
    env_data = {}
    if os.path.exists(".env"):
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        env_data[key.strip()] = val.strip()
        except Exception:
            pass
    return env_data

def generate_configs(hw: Dict, mac_strategy: Optional[str], selected_models: List[str], data_dir: str, openclaw_token: str):
    print(f"\n{Color.CYAN}⚙️  Generating customized environment and configuration files...{Color.ENDC}")
    
    # 1. Generate .env file
    env_content = []
    
    existing_env = read_existing_env()
    db_password = existing_env.get("DB_PASSWORD") or os.getenv("DB_PASSWORD") or ("webui-secure-password-" + str(int(time.time()))[-4:])
    port = existing_env.get("PORT") or "8080"
    ollama_port = existing_env.get("OLLAMA_PORT") or "11434"
    webui_secret = existing_env.get("OPEN_WEBUI_SECRET_KEY") or os.getenv("OPEN_WEBUI_SECRET_KEY") or ("secret-" + str(int(time.time())))
    openclaw_port = existing_env.get("OPENCLAW_PORT") or "18789"
    
    env_content.append("# Generated by setup.py")
    env_content.append(f"PORT={port}")
    env_content.append(f"OLLAMA_PORT={ollama_port}")
    env_content.append(f"OPEN_WEBUI_SECRET_KEY={webui_secret}")
    env_content.append("DB_HOST=db")
    env_content.append("DB_PORT=5432")
    env_content.append("DB_USER=webui")
    env_content.append(f"DB_PASSWORD={db_password}")
    env_content.append("DB_NAME=webui")
    env_content.append(f"DATA_DIR={data_dir}")
    env_content.append(f"OPENCLAW_PORT={openclaw_port}")
    env_content.append(f"OPENCLAW_GATEWAY_TOKEN={openclaw_token}")
    
    use_native_ollama = (hw['os'] == 'Darwin' and mac_strategy == 'native')
    
    if use_native_ollama:
        env_content.append("OLLAMA_BASE_URL=http://host.docker.internal:11434")
    else:
        env_content.append("OLLAMA_BASE_URL=http://ollama:11434")
        
    with open(".env", "w") as f:
        f.write("\n".join(env_content) + "\n")
    print(f"  ✅ Written: {Color.BOLD}.env{Color.ENDC}")
    
    # Pre-create data directories to prevent root permission locks from Docker Compose
    try:
        resolved_data_dir = os.path.abspath(os.path.expanduser(data_dir))
        os.makedirs(os.path.join(resolved_data_dir, "postgres"), exist_ok=True)
        os.makedirs(os.path.join(resolved_data_dir, "open-webui"), exist_ok=True)
        if not use_native_ollama:
            os.makedirs(os.path.join(resolved_data_dir, "ollama"), exist_ok=True)
        
        openclaw_dir = os.path.join(resolved_data_dir, "openclaw")
        os.makedirs(openclaw_dir, exist_ok=True)
        
        # Write default openclaw.json configuration file to pass the gateway mode verification
        openclaw_config_path = os.path.join(openclaw_dir, "openclaw.json")
        if not os.path.exists(openclaw_config_path):
            openclaw_models = []
            for model_id in selected_models:
                model_name = model_id
                for m in MODEL_CATALOG:
                    if m['id'] == model_id:
                        model_name = m['name']
                        break
                openclaw_models.append({
                    "id": model_id,
                    "name": model_name
                })
                
            ollama_api_url = "http://host.docker.internal:11434/v1" if use_native_ollama else "http://ollama:11434/v1"
            
            default_config = {
                "gateway": {
                    "mode": "local"
                },
                "models": {
                    "providers": {
                        "ollama": {
                            "baseUrl": ollama_api_url,
                            "apiKey": "ollama",
                            "api": "openai-completions",
                            "models": openclaw_models
                        }
                    }
                }
            }
            with open(openclaw_config_path, "w") as config_file:
                json.dump(default_config, config_file, indent=2)
            print(f"  ✅ Initialized OpenClaw config with your selected models: {Color.BOLD}{openclaw_config_path}{Color.ENDC}")
    except Exception as e:
        print(f"  {Color.WARNING}⚠️  Warning pre-creating data directories: {e}{Color.ENDC}")
    
    # 2. Generate custom docker-compose.yml
    compose_yaml = []
    compose_yaml.append("services:")
    
    # DB Service
    compose_yaml.append("  db:")
    compose_yaml.append("    image: postgres:16-alpine")
    compose_yaml.append("    container_name: webui-postgres")
    compose_yaml.append("    restart: always")
    compose_yaml.append("    environment:")
    compose_yaml.append("      POSTGRES_USER: webui")
    compose_yaml.append(f"      POSTGRES_PASSWORD: {db_password}")
    compose_yaml.append("      POSTGRES_DB: webui")
    compose_yaml.append("    volumes:")
    compose_yaml.append(f"      - {data_dir}/postgres:/var/lib/postgresql/data")
    compose_yaml.append("    healthcheck:")
    compose_yaml.append("      test: [\"CMD-SHELL\", \"pg_isready -U webui -d webui\"]")
    compose_yaml.append("      interval: 5s")
    compose_yaml.append("      timeout: 5s")
    compose_yaml.append("      retries: 5")
    compose_yaml.append("")
    
    # Ollama Service (Only if not native on Mac)
    if not use_native_ollama:
        compose_yaml.append("  ollama:")
        compose_yaml.append("    image: ollama/ollama:latest")
        compose_yaml.append("    container_name: ollama-server")
        compose_yaml.append("    restart: always")
        compose_yaml.append("    ports:")
        compose_yaml.append(f"      - \"{ollama_port}:11434\"")
        compose_yaml.append("    volumes:")
        compose_yaml.append(f"      - {data_dir}/ollama:/root/.ollama")
        
        # If GPU detected on Linux/Windows host, configure GPU pass-through
        if hw['gpu_name'] and hw['os'] != 'Darwin':
            print(f"  🔥 Configuring NVIDIA GPU hardware acceleration in docker-compose.yml...")
            compose_yaml.append("    deploy:")
            compose_yaml.append("      resources:")
            compose_yaml.append("        reservations:")
            compose_yaml.append("          devices:")
            compose_yaml.append("            - driver: nvidia")
            compose_yaml.append("              count: all")
            compose_yaml.append("              capabilities: [gpu]")
        compose_yaml.append("")
        
    # Open WebUI Service
    compose_yaml.append("  open-webui:")
    compose_yaml.append("    image: ghcr.io/open-webui/open-webui:main")
    compose_yaml.append("    container_name: open-webui-client")
    compose_yaml.append("    restart: always")
    compose_yaml.append("    ports:")
    compose_yaml.append(f"      - \"{port}:8080\"")
    compose_yaml.append("    environment:")
    compose_yaml.append(f"      - DATABASE_URL=postgresql://webui:{db_password}@db:5432/webui")
    
    if use_native_ollama:
        compose_yaml.append("      - OLLAMA_BASE_URL=http://host.docker.internal:11434")
    else:
        compose_yaml.append("      - OLLAMA_BASE_URL=http://ollama:11434")
        
    compose_yaml.append(f"      - WEBUI_SECRET_KEY={webui_secret}")
    compose_yaml.append("      - WEBUI_NAME=Local LLM Stack")
    compose_yaml.append("    volumes:")
    compose_yaml.append(f"      - {data_dir}/open-webui:/app/backend/data")
    
    # Extra hosts needed for resolving host.docker.internal on native setup
    if use_native_ollama:
        compose_yaml.append("    extra_hosts:")
        compose_yaml.append("      - \"host.docker.internal:host-gateway\"")
        
    compose_yaml.append("    depends_on:")
    compose_yaml.append("      db:")
        # Wait, since open-webui depends on postgres db being healthy, we keep it
    compose_yaml.append("        condition: service_healthy")
    
    if not use_native_ollama:
        compose_yaml.append("      ollama:")
        compose_yaml.append("        condition: service_started")
        
    compose_yaml.append("")
    
    # OpenClaw Gateway Service
    compose_yaml.append("  openclaw-gateway:")
    compose_yaml.append("    image: ghcr.io/openclaw/openclaw:latest")
    compose_yaml.append("    container_name: openclaw-gateway")
    compose_yaml.append("    restart: always")
    compose_yaml.append("    ports:")
    compose_yaml.append(f"      - \"127.0.0.1:{openclaw_port}:18789\"")
    compose_yaml.append("    environment:")
    compose_yaml.append("      - HOME=/home/node")
    compose_yaml.append("      - OPENCLAW_HOME=/home/node")
    compose_yaml.append("      - OPENCLAW_STATE_DIR=/home/node/.openclaw")
    compose_yaml.append("      - OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json")
    compose_yaml.append("      - OPENCLAW_CONFIG_DIR=/home/node/.openclaw")
    compose_yaml.append("      - OPENCLAW_WORKSPACE_DIR=/home/node/.openclaw/workspace")
    compose_yaml.append(f"      - OPENCLAW_GATEWAY_TOKEN={openclaw_token}")
    compose_yaml.append("    volumes:")
    compose_yaml.append(f"      - {data_dir}/openclaw:/home/node/.openclaw")
    compose_yaml.append("")
    
    # Write custom file
    with open("docker-compose.yml", "w") as f:
        f.write("\n".join(compose_yaml) + "\n")
    print(f"  ✅ Written: {Color.BOLD}docker-compose.yml{Color.ENDC}")

def launch_containers() -> bool:
    print(f"\n{Color.CYAN}🐳 Starting the Docker stack...{Color.ENDC}")
    
    # Try modern 'docker compose' first
    try:
        cmd = ['docker', 'compose', 'up', '-d']
        res = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
        if res.returncode == 0:
            print(f"\n{Color.GREEN}✅ Docker containers launched successfully!{Color.ENDC}")
            return True
        else:
            print(f"\n{Color.WARNING}⚠️  'docker compose' failed. Retrying with legacy 'docker-compose'...{Color.ENDC}")
    except FileNotFoundError:
        print(f"\n{Color.WARNING}⚠️  'docker' executable not found on path.{Color.ENDC}")
    except Exception as e:
        print(f"\n{Color.WARNING}⚠️  Error running 'docker compose': {e}{Color.ENDC}")

    # Fall back to legacy 'docker-compose'
    try:
        cmd = ['docker-compose', 'up', '-d']
        res = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
        if res.returncode == 0:
            print(f"\n{Color.GREEN}✅ Docker containers launched successfully!{Color.ENDC}")
            return True
        else:
            print(f"\n{Color.FAIL}❌ Failed to start containers using legacy docker-compose.{Color.ENDC}")
            return False
    except FileNotFoundError:
        print(f"\n{Color.FAIL}❌ Neither 'docker compose' nor 'docker-compose' succeeded.{Color.ENDC}")
        print("Please check that the Docker daemon is running and you have appropriate permissions.")
        print("If you are running on Linux, you may need to run this script as sudo.")
        return False
    except Exception as e:
        print(f"\n{Color.FAIL}❌ Error running fallback docker-compose command: {e}{Color.ENDC}")
        return False

def wait_for_ollama(endpoint: str, timeout_seconds: int = 120) -> bool:
    print(f"\n{Color.CYAN}⏳ Connecting to Ollama API at {endpoint}...{Color.ENDC}")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            req = urllib.request.Request(f"{endpoint}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    print(f"{Color.GREEN}✅ Connected to Ollama successfully!{Color.ENDC}")
                    return True
        except Exception:
            pass
        print(f"{Color.GRAY}Waiting for Ollama API to boot... (Checking again in 3s){Color.ENDC}")
        time.sleep(3)
    return False

def pull_ollama_model(endpoint: str, model_id: str):
    print(f"\n{Color.BOLD}📥 Pulling LLM Model: {model_id}{Color.ENDC}")
    url = f"{endpoint}/api/pull"
    payload = json.dumps({"name": model_id}).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            last_status = ""
            # Parse streaming json response
            for line in response:
                if not line:
                    continue
                try:
                    data = json.loads(line.decode('utf-8'))
                    status = data.get('status', '')
                    completed = data.get('completed', 0)
                    total = data.get('total', 0)
                    
                    if total > 0:
                        pct = (completed / total) * 100
                        # Build simple text progress bar
                        filled_len = int(30 * completed // total)
                        bar = '=' * filled_len + '-' * (30 - filled_len)
                        print(f"\r  [{bar}] {pct:5.1f}% | {completed / (1024**2):.1f}/{total / (1024**2):.1f} MB | {status}", end="", flush=True)
                    else:
                        if status != last_status:
                            print(f"\n  ℹ️  {status}", end="", flush=True)
                            last_status = status
                except Exception:
                    pass
            print(f"\n{Color.GREEN}  ✅ Success: {model_id} downloaded!{Color.ENDC}")
    except Exception as e:
        print(f"\n{Color.FAIL}  ❌ Error pulling {model_id}: {e}{Color.ENDC}")
        print("  Please check network connectivity or run: ollama pull " + model_id)

def main():
    clear_screen()
    print_banner()
    
    # 1. System Discovery
    hw = detect_hardware()
    print_hardware_report(hw)
    
    # 2. Dependency Check
    if not check_dependencies():
        sys.exit(1)
        
    # 3. macOS Native setup vs Docker check
    mac_strategy = None
    if hw['os'] == 'Darwin':
        mac_strategy = setup_mac_options(hw)
        
    # 4. Model Selection
    selected_models = select_models(hw)
    
    # 5. Data Directory Selection
    data_dir = "./data"
    if os.path.exists("/workspace") and os.path.isdir("/workspace"):
        print(f"\n{Color.CYAN}ℹ️  RunPod host environment detected (/workspace is available).{Color.ENDC}")
        print("To keep your databases, users, and models safe during GPU changes,")
        print("they must be saved under /workspace.")
        use_workspace = input("Configure persistence path to /workspace? (Y/n): ").strip().lower()
        if use_workspace != 'n':
            data_dir = "/workspace"
    else:
        print(f"\n{Color.CYAN}📂 Data Persistence Config{Color.ENDC}")
        custom_dir = input("Enter directory path to store database & model data [default: ./data]: ").strip()
        if custom_dir:
            data_dir = custom_dir
            
    # 6. Generate Configuration Files
    existing_env = read_existing_env()
    openclaw_token = existing_env.get("OPENCLAW_GATEWAY_TOKEN") or os.getenv("OPENCLAW_GATEWAY_TOKEN") or ("claw-token-" + str(int(time.time())))
    generate_configs(hw, mac_strategy, selected_models, data_dir, openclaw_token)
    
    # 7. Launch Docker Containers
    if not launch_containers():
        sys.exit(1)
        
    # 8. Check and pull models
    # Ollama endpoint determination
    if hw['os'] == 'Darwin' and mac_strategy == 'native':
        ollama_endpoint = "http://localhost:11434"
    else:
        # Dockerized Ollama runs on port 11434 of the local host too
        ollama_endpoint = "http://localhost:11434"
        
    if selected_models:
        # Wait for Ollama service to be ready
        if wait_for_ollama(ollama_endpoint):
            for model in selected_models:
                pull_ollama_model(ollama_endpoint, model)
        else:
            print(f"\n{Color.FAIL}❌ Ollama API did not become available in time. Skipping automatic pulls.{Color.ENDC}")
            print(f"You can pull models manually using: {Color.BOLD}docker exec -it ollama-server ollama pull <model-name>{Color.ENDC}")
            
    # 9. Finished!
    print(f"\n{Color.GREEN}{Color.BOLD}🎉 Setup Completed Successfully!{Color.ENDC}")
    print(f"============================================================")
    print(f"📱  {Color.BOLD}Open WebUI:{Color.ENDC} http://localhost:8080")
    print(f"🤖  {Color.BOLD}OpenClaw Gateway:{Color.ENDC} http://localhost:18789")
    print(f"🔑  {Color.BOLD}OpenClaw Token:{Color.ENDC} {openclaw_token}")
    print(f"🦙  {Color.BOLD}Ollama API:{Color.ENDC} {ollama_endpoint}")
    print(f"🗄️   {Color.BOLD}PostgreSQL DB:{Color.ENDC} Running on container 'webui-postgres'")
    print(f"============================================================")
    
    if hw['os'] == 'Darwin' and mac_strategy == 'native':
        print(f"\n{Color.WARNING}{Color.BOLD}IMPORTANT NATIVE OLLAMA NOTE:{Color.ENDC}")
        print("Since you chose Native Host Ollama, please ensure Ollama is running on your Mac.")
        print("If you haven't installed it, download it from: https://ollama.com")
        print("Make sure it's active in your menu bar before connecting Open WebUI.")
        
    print(f"\nCreate your admin account when you open Open WebUI in your browser.")
    print("Happy chatting! 🚀\n")

if __name__ == "__main__":
    main()
