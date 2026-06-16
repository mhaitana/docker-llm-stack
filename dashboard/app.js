// --- Config ---
const OLLAMA_ENDPOINT = 'http://localhost:11434';
const WEBUI_ENDPOINT = 'http://localhost:8080';
const OPENCLAW_ENDPOINT = 'http://localhost:18789';

// --- DOM Elements ---
const modelsLoading = document.getElementById('models-loading');
const noModelsMsg = document.getElementById('no-models-msg');
const modelsTable = document.getElementById('models-table');
const modelsListTbody = document.getElementById('models-list-tbody');

const pullForm = document.getElementById('pull-model-form');
const modelTagInput = document.getElementById('model-tag-input');
const btnPullSubmit = document.getElementById('btn-pull-submit');

const pullProgressContainer = document.getElementById('pull-progress-container');
const pullStatusText = document.getElementById('pull-status-text');
const pullPercentText = document.getElementById('pull-percent-text');
const progressBarFill = document.getElementById('progress-bar-fill');
const pullSpeedText = document.getElementById('pull-speed-text');
const pullDownloadedText = document.getElementById('pull-downloaded-text');

// --- Helper: Format Size ---
function formatBytes(bytes) {
    if (!bytes) return '0.00 GB';
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(2)} GB`;
}

// --- Service Health Checker ---
async function pingService(endpoint, elementId) {
    const indicator = document.querySelector(`#${elementId} .status-indicator`);
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2500);
        
        // no-cors mode allows requests to succeed even if CORS blocks reading the response content
        await fetch(endpoint, {
            mode: 'no-cors',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        indicator.className = 'status-indicator pulse-online';
    } catch (e) {
        indicator.className = 'status-indicator pulse-offline';
    }
}

async function checkAllServices() {
    pingService(WEBUI_ENDPOINT, 'srv-webui');
    pingService(OPENCLAW_ENDPOINT, 'srv-openclaw');
    pingService(OLLAMA_ENDPOINT, 'srv-ollama');
}

// --- Fetch & Render Models List ---
async function fetchModels() {
    try {
        const response = await fetch(`${OLLAMA_ENDPOINT}/api/tags`);
        if (!response.ok) throw new Error('Ollama offline');
        
        const data = await response.json();
        const models = data.models || [];
        
        modelsLoading.style.display = 'none';
        
        if (models.length === 0) {
            noModelsMsg.style.display = 'block';
            modelsTable.style.display = 'none';
            return;
        }
        
        noModelsMsg.style.display = 'none';
        modelsTable.style.display = 'table';
        
        modelsListTbody.innerHTML = '';
        models.forEach(model => {
            const row = document.createElement('tr');
            
            // Extract details safely
            const name = model.name;
            const size = formatBytes(model.size);
            const format = model.details?.format || 'gguf';
            const family = model.details?.family || 'llama';
            
            row.innerHTML = `
                <td>${name}</td>
                <td>${size}</td>
                <td><span class="port-label">${format}</span></td>
                <td>${family}</td>
            `;
            modelsListTbody.appendChild(row);
        });
    } catch (err) {
        modelsLoading.style.display = 'none';
        noModelsMsg.style.display = 'block';
        noModelsMsg.innerHTML = `<p style="color: var(--error)">⚠️ Failed to connect to Ollama. Make sure it is running.</p>`;
        modelsTable.style.display = 'none';
    }
}

// --- Pull Model Stream Handler ---
async function pullModel(modelName) {
    // UI states
    btnPullSubmit.disabled = true;
    modelTagInput.disabled = true;
    pullProgressContainer.style.display = 'flex';
    progressBarFill.style.width = '0%';
    pullPercentText.textContent = '0.0%';
    pullStatusText.textContent = `Starting download for ${modelName}...`;
    pullSpeedText.textContent = '0 MB/s';
    pullDownloadedText.textContent = 'Initializing...';
    
    let lastCompleted = 0;
    let lastTime = Date.now();
    
    try {
        const response = await fetch(`${OLLAMA_ENDPOINT}/api/pull`, {
            method: 'POST',
            body: JSON.stringify({ name: modelName }),
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) throw new Error('Ollama pull request failed');
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // save trailing line
            
            for (const line of lines) {
                if (!line.trim()) continue;
                
                try {
                    const payload = JSON.parse(line);
                    const status = payload.status || 'pulling';
                    
                    if (payload.total && payload.completed) {
                        const total = payload.total;
                        const completed = payload.completed;
                        const pct = ((completed / total) * 100).toFixed(1);
                        
                        // Calculate speed
                        const now = Date.now();
                        const timeDiff = (now - lastTime) / 1000; // in seconds
                        if (timeDiff >= 0.5) {
                            const bytesDiff = completed - lastCompleted;
                            const speedMbps = (bytesDiff / timeDiff) / (1024 ** 2);
                            pullSpeedText.textContent = `${speedMbps.toFixed(1)} MB/s`;
                            
                            lastCompleted = completed;
                            lastTime = now;
                        }
                        
                        // Update UI
                        progressBarFill.style.width = `${pct}%`;
                        pullPercentText.textContent = `${pct}%`;
                        pullStatusText.textContent = status;
                        pullDownloadedText.textContent = `${(completed / (1024**2)).toFixed(0)} / ${(total / (1024**2)).toFixed(0)} MB`;
                    } else {
                        pullStatusText.textContent = status;
                    }
                } catch (e) {
                    // JSON parse warning
                }
            }
        }
        
        // Success
        pullStatusText.textContent = 'Success! Model downloaded.';
        progressBarFill.style.width = '100%';
        pullPercentText.textContent = '100%';
        setTimeout(() => {
            pullProgressContainer.style.display = 'none';
            btnPullSubmit.disabled = false;
            modelTagInput.disabled = false;
            modelTagInput.value = '';
            fetchModels();
        }, 3000);
        
    } catch (err) {
        pullStatusText.textContent = `Error: ${err.message}`;
        progressBarFill.style.background = 'var(--error)';
        setTimeout(() => {
            pullProgressContainer.style.display = 'none';
            progressBarFill.style.background = 'linear-gradient(90deg, var(--primary) 0%, var(--success) 100%)';
            btnPullSubmit.disabled = false;
            modelTagInput.disabled = false;
        }, 5000);
    }
}

// --- Event Listeners ---
pullForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const tag = modelTagInput.value.strip ? modelTagInput.value.strip() : modelTagInput.value.trim();
    if (tag) {
        pullModel(tag);
    }
});

// Copy OpenClaw token to clipboard
const copyBtn = document.getElementById('btn-copy-token');
const tokenVal = document.getElementById('openclaw-token-value');
if (copyBtn && tokenVal) {
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(tokenVal.textContent.trim());
        copyBtn.textContent = '✅';
        setTimeout(() => {
            copyBtn.textContent = '📋';
        }, 2000);
    });
}

// --- Initial Startup Loops ---
checkAllServices();
fetchModels();

// Poll service health every 5 seconds
setInterval(checkAllServices, 5000);
