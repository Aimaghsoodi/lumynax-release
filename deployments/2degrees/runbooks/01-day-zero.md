# Runbook · Day zero — first time on a fresh box

**Goal:** from `ssh root@new-host` to serving real APIs in 60-90 min.

## 1. Provision (~10 min)

```bash
# On the host
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin curl jq git python3 python3-pip openssl

# NVIDIA Container Toolkit (skip if already there)
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

## 2. Clone (~1 min)

```bash
git clone https://github.com/Aimaghsoodi/lumynax-release
cd lumynax-release/deployments/2degrees
```

## 3. Provide HF token

```bash
export HF_TOKEN=hf_REPLACE_WITH_YOUR_OWN
```

## 4. Walk the scripts

```bash
bash scripts/00-preflight.sh
bash scripts/01-bootstrap.sh

# Pick your starter set — 3 small models will be ~20 GB total and fit on any GPU
bash scripts/02-pull-weights.sh \
  lumynax-chat-hermes-3-llama31-8b-gguf \
  lumynax-coder-deepseek-v2-lite-16b-gguf \
  lumynax-embed-bge-m3

bash scripts/04-serve.sh

# Smoke test
ADMIN_KEY=$(cat state/admin-key)
curl -fsS -H "Authorization: Bearer $ADMIN_KEY" http://localhost:8080/v1/models | jq -r '.data[].id'
```

## 5. Issue your first customer key

```bash
bash scripts/05-issue-key.sh "Pilot Tenant" --jurisdiction NZ --min-tier 3 --rate-limit 500
# Send state/onboarding/pilot-tenant.md to them via an encrypted channel.
```

## 6. Optional: expose via nginx + TLS

```bash
# Install nginx + certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Reverse proxy to localhost:8080
sudo tee /etc/nginx/sites-available/lumynax <<NGX
server {
    listen 80;
    server_name $LUMYNAX_PUBLIC_HOST;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 600;
        proxy_buffering off;
    }
}
NGX
sudo ln -sf /etc/nginx/sites-available/lumynax /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d $LUMYNAX_PUBLIC_HOST
```

## 7. Confirm and call it day-zero done

```bash
bash scripts/06-monitor.sh    # tmux session, leave running
```

Check daily that the audit log is being written, GPUs aren't saturated, and the gateway is healthy.
