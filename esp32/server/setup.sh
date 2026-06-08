#!/bin/bash
# ESP32-S3 AI Assistant — Server Setup Script
#
# Creates required directories and config files.
# Run once before `docker compose up -d`.

set -e
cd "$(dirname "$0")"

echo "=== ESP32-S3 AI Assistant Server Setup ==="
echo ""

# Load .env if it exists
if [ -f .env ]; then
    source .env
    echo "[OK] Loaded .env"
else
    echo "[!!] .env not found — copying from .env.example"
    cp .env.example .env
    echo "     Please edit .env with your settings, then re-run this script."
    exit 1
fi

SERVER_IP="${SERVER_IP:-192.168.1.100}"

# Create directories
echo ""
echo "--- Creating directories ---"
mkdir -p data uploadfile mysql/data openclaw-data
echo "[OK] Directories created"

# Create .config.yaml for Xiaozhi server (from API mode)
if [ ! -f data/.config.yaml ]; then
    echo ""
    echo "--- Creating data/.config.yaml ---"
    cat > data/.config.yaml << EOF
# Xiaozhi ESP32 Server — Configuration (Full Module / API Mode)
#
# IMPORTANT: After first startup:
#   1. Open 智控台: http://${SERVER_IP}:${XIAOZHI_WEB_PORT:-8002}
#   2. Register admin account (first user = superadmin)
#   3. Go to 参数管理 → find server.secret → copy the 参数值
#   4. Paste it below in manager-api.secret
#   5. Run: docker compose restart xiaozhi-esp32-server

server:
  ip: 0.0.0.0
  port: 8000
  http_port: 8003

manager-api:
  # Docker internal URL for 智控台
  url: http://xiaozhi-esp32-server-web:8002/xiaozhi
  # Paste server.secret from 智控台 → 参数管理
  secret: PASTE_YOUR_SERVER_SECRET_HERE

# Default system prompt
prompt_template: agent-base-prompt.txt
EOF
    echo "[OK] data/.config.yaml created"
    echo "     >> You must update manager-api.secret after first startup!"
else
    echo "[OK] data/.config.yaml already exists (skipping)"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env if you haven't already"
echo "  2. docker compose up -d"
echo "  3. Wait ~30s for MySQL to initialize"
echo "  4. Open 智控台: http://${SERVER_IP}:${XIAOZHI_WEB_PORT:-8002}"
echo "  5. Register admin account (first user = superadmin)"
echo "  6. Go to 参数管理 → copy server.secret value"
echo "  7. Paste into data/.config.yaml → manager-api.secret"
echo "  8. docker compose restart xiaozhi-esp32-server"
echo ""
echo "After server.secret is configured:"
echo "  - 智控台: http://${SERVER_IP}:${XIAOZHI_WEB_PORT:-8002}"
echo "  - WebSocket: ws://${SERVER_IP}:${XIAOZHI_WS_PORT:-8000}/xiaozhi/v1/"
echo "  - OTA: http://${SERVER_IP}:${XIAOZHI_HTTP_PORT:-8003}/xiaozhi/ota/"
echo "  - OpenClaw: http://${SERVER_IP}:${OPENCLAW_PORT:-18789}/v1/chat/completions"
