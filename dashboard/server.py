import http.server
import socketserver
import json
import os
import urllib.request
import sys

PORT = 8000

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Allow CORS for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/sync-openclaw':
            self.handle_sync_openclaw()
        else:
            self.send_error(404, "File not found")

    def handle_sync_openclaw(self):
        try:
            # 1. Fetch current models from Ollama
            ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
            req = urllib.request.Request(f"{ollama_endpoint}/api/tags")
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    models = data.get('models', [])
            except Exception as e:
                # If host.docker.internal fails, try localhost (for cases where it runs inside the same network)
                try:
                    req2 = urllib.request.Request("http://localhost:11434/api/tags")
                    with urllib.request.urlopen(req2, timeout=3) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        models = data.get('models', [])
                except Exception:
                    raise Exception(f"Failed to connect to Ollama at {ollama_endpoint}: {e}")

            model_names = [m['name'] for m in models]

            # 2. Determine which openclaw.json files to update
            config_paths = []
            
            # Check docker openclaw config mount
            docker_config = "/data/openclaw/openclaw.json"
            if os.path.exists(os.path.dirname(docker_config)):
                config_paths.append(docker_config)
                
            # Check native openclaw config mount
            native_config = "/native-openclaw/openclaw.json"
            if os.path.exists(os.path.dirname(native_config)):
                config_paths.append(native_config)

            updated_paths = []
            for config_path in config_paths:
                try:
                    os.makedirs(os.path.dirname(config_path), exist_ok=True)
                    if os.path.exists(config_path):
                        with open(config_path, "r") as f:
                            config = json.load(f)
                    else:
                        config = {}

                    # Ensure structural dictionaries exist
                    if "agents" not in config:
                        config["agents"] = {}
                    if "defaults" not in config["agents"]:
                        config["agents"]["defaults"] = {}
                    if "model" not in config["agents"]["defaults"]:
                        config["agents"]["defaults"]["model"] = {}

                    # Rebuild models catalog containing only currently available models
                    openclaw_models_catalog = {}
                    for m in model_names:
                        openclaw_models_catalog[f"ollama/{m}"] = {}
                    # Add provider wildcard
                    openclaw_models_catalog["ollama/*"] = {}
                    config["agents"]["defaults"]["models"] = openclaw_models_catalog

                    # Update primary model if needed
                    current_primary = config["agents"]["defaults"]["model"].get("primary", "")
                    if model_names:
                        if not current_primary or not any(current_primary.endswith(m) for m in model_names):
                            config["agents"]["defaults"]["model"]["primary"] = f"ollama/{model_names[0]}"
                    else:
                        config["agents"]["defaults"]["model"]["primary"] = ""

                    with open(config_path, "w") as f:
                        json.dump(config, f, indent=2)
                    updated_paths.append(config_path)
                except Exception as ex:
                    print(f"Error updating config path {config_path}: {ex}", file=sys.stderr)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response_data = {"status": "success", "updated_paths": updated_paths, "models": model_names}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response_data = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Serving dashboard backend on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
