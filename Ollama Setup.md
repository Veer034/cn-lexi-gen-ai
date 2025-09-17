# Ollama + Mistral 3B on Azure **D8as v4** (Production README)

This guide configures a **Standard D8as v4** VM (8 vCPUs, 32 GiB RAM, no GPU) to serve **Ollama** with a small LLM (e.g., **Mistral 3B** or **BLOOMZ 3B**) for multilingual classification + RAG answer generation. It includes CPU tuning, huge pages, a hardened systemd unit, and tips for throughput (10–15 req/s target).

---

## 1) VM & Disk Prereqs

- **Size:** Standard **D8as v4** (8 vCPUs, 32 GiB RAM)
- **OS:** Ubuntu 22.04 LTS (Jammy)
- **Disk:** Premium SSD recommended, **/var/lib/ollama** on the fastest disk.
- **Network:** Restrict access with NSG / firewall; avoid exposing the API to the public internet directly.

---

## 2) Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo mkdir -p /var/lib/ollama
sudo chown -R $USER:$USER /var/lib/ollama
```

> **Model choice**
>
> • If available in your registry: `mistral:3b` (fast, compact).
>
> • Alternative multilingual: `bloomz:3b`.
>
> • If your registry doesn’t have a `:3b` tag, use the closest small instruct model you’ve tested (e.g., `mistral:latest` or a quantized variant) and update `MODEL_ID` below.

Pull the model (example uses a variable so you can swap cleanly):

```bash
MODEL_ID="mistral:3b"   # or: MODEL_ID="bloomz:3b" (or your tested small model tag)
ollama pull "$MODEL_ID"
```

---

## 3) Huge Pages (fewer TLB misses, faster memory access)

- Default Linux pages are 4 KB; huge pages are **2 MB**.
- For a \~**4.1 GB** small model, reserve \~**2,200** huge pages (≈ 4.29 GB) to cover weights + a buffer.

```bash
# Temporary (until reboot)
sudo sysctl -w vm.nr_hugepages=2200

# Make permanent
echo "vm.nr_hugepages=2200" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Verify
grep Huge /proc/meminfo
```

Expected:

```
HugePages_Total:  2200
HugePages_Free:   2200
Hugepagesize:     2048 kB
```

> **Note:** Transparent Huge Pages (THP) may already show `AnonHugePages`. Pre‑allocating `vm.nr_hugepages` is more predictable for LLM weights.

---

## 4) Production systemd unit for Ollama

Create `/etc/systemd/system/ollama.service`:

```ini
[Unit]
Description=Ollama Inference API
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
WorkingDirectory=/var/lib/ollama
Restart=always
RestartSec=5
StartLimitIntervalSec=0

# ==== Ollama Tuning for Azure E8as v4 (8 vCPUs, 32GB RAM) ====
# Network configuration
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_ORIGINS=http://10.0.0.7:*,http://localhost:*"

# Concurrency optimized for multiple concurrent requests
Environment="OLLAMA_NUM_PARALLEL=6"      # Increased from 4 (better for 8 vCPUs)
Environment="OLLAMA_MAX_QUEUE=20"        # Increased queue size

# Memory management for 32GB RAM
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=1800"     # 30 min cache

# CPU optimization - reserve cores for concurrency
Environment="OLLAMA_NUMA_PINNING=0"
Environment="OLLAMA_CPU_THREADS=4"       # Use 4 cores per request (allows 2 concurrent)

# Memory allocation (more conservative)
Environment="OLLAMA_MAX_VRAM=0"          # CPU-only mode

# Model-specific memory control
Environment="OLLAMA_FLASH_ATTENTION=1"   # Enable flash attention for efficiency
Environment="OLLAMA_KV_CACHE_TYPE=f16"   # Use f16 for KV cache to save memory

# ==== Resource Limits (More realistic for 32GB) ====
LimitNOFILE=65536
LimitNPROC=8192                          # Increased for more threads
LimitAS=28G                              # Use more of available 32GB
LimitMEMLOCK=24G                         # Allow more memory for models
LimitCORE=0                              # Disable core dumps to save space

# ==== Performance Tuning ====
# Disable swap usage for better performance
Environment="OLLAMA_MMAP_DISABLE=0"      # Keep mmap enabled
Environment="OLLAMA_TMPDIR=/tmp/ollama"   # Use fast temp directory

# ==== Logging ====
StandardOutput=append:/var/log/ollama/service.log
StandardError=append:/var/log/ollama/error.log
SyslogIdentifier=ollama

[Install]
WantedBy=multi-user.target
```

Allow AI Services from private network to hit ollama:

```
Create the log directory:


```

sudo mkdir -p /var/log/ollama
sudo chown ollama:ollama /var/log/ollama

```
Create the working directory:


```

sudo mkdir -p /var/lib/ollama
sudo chown ollama:ollama /var/lib/ollama

```
Reload and restart the service:

```

sudo systemctl daemon-reload
sudo systemctl restart ollama

```


# Enable UFW
sudo ufw --force enable


#allowing specific Ip address
sudo ufw allow from 10.0.0.7 to any port 11434
sudo ufw status

az network nsg rule create \
  --resource-group convonest-prod-ai \
  --nsg-name ai-modelsNSG \
  --name Allow-Ollama \
  --priority 100 \
  --source-address-prefixes 10.0.0.7/32 \
  --destination-port-ranges 11434 \
  --access Allow \
  --protocol Tcp
```

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama
sudo systemctl status ollama --no-pager
```

> **Log rotation:** Configure `/etc/logrotate.d/ollama` to prevent unbounded log growth.

---

## 5) API Usage (with streaming)

**Streaming is production‑safe** and lowers perceived latency.

### cURL example

```bash
curl -N http://localhost:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "'"$MODEL_ID"'",
    "prompt": "Classify the email as complaint/query/suggestion and draft a 2‑sentence reply.",
    "stream": true
  }'
```

### Minimal Python example

```python
import requests
import json

url = "http://localhost:11434/api/generate"
payload = {
  "model": "mistral:3b",  # or your MODEL_ID
  "prompt": "Answer in Hindi: क्या स्टेटस है?",
  "stream": True
}
with requests.post(url, json=payload, stream=True) as r:
    for line in r.iter_lines():
        if line:
            msg = json.loads(line)
            print(msg.get("response", ""), end="", flush=True)
```

---

## 6) Throughput Playbook (D8as v4)

- Start with `OLLAMA_NUM_PARALLEL=5`, `OLLAMA_MAX_QUEUE=40`.
- For **short classification** (few tokens out), expect high QPS.
- For **generation** (multi‑sentence), throughput is lower; scale horizontally with multiple VMs or run multiple Ollama instances bound to separate CPU sets.
- Use **quantized** models (e.g., Q4_K_M) to reduce latency with minimal quality loss.

---

## 7) Security Checklist

- Lock CORS to trusted origins: `OLLAMA_ORIGINS=https://yourapp.example`.
- Put the service behind a private VNet + Application Gateway/NGINX.
- Use authentication/authorization at the gateway layer.
- Keep the VM patched (`unattended-upgrades`).

---

## 8) Troubleshooting

- **`HugePages_Total: 0`** → allocate huge pages again; ensure enough free RAM.
- **Rejected requests** → increase `OLLAMA_MAX_QUEUE` or scale out.
- **High latency** → reduce `NUM_PARALLEL` or upgrade to D16as v4; verify CPU is in `performance` governor.
- **Out of memory** → reduce concurrency or use a smaller/quantized model.

---

## Appendix: Persist CPU governor on boot

Create `/etc/systemd/system/cpu-performance.service`:

```ini
[Unit]
Description=Force CPU governor to performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > "$g"; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cpu-performance
sudo systemctl start cpu-performance
```
