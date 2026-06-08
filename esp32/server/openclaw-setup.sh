#!/bin/sh
set -e

# Install OpenClaw if not already present
if ! command -v openclaw >/dev/null 2>&1; then
  echo "=== Installing OpenClaw ==="
  npm install -g openclaw
fi

# Configure gateway for LAN access and enable OpenAI-compatible API
echo "=== Configuring OpenClaw Gateway ==="
openclaw config set gateway.bind lan 2>/dev/null || true
openclaw config set gateway.http.endpoints.chatCompletions.enabled true 2>/dev/null || true
openclaw config set gateway.http.endpoints.responses.enabled true 2>/dev/null || true

# Start the gateway in foreground
echo "=== Starting OpenClaw Gateway ==="
echo "  Port: ${OPENCLAW_GATEWAY_PORT:-18789}"
echo "  Bind: ${OPENCLAW_GATEWAY_BIND:-0.0.0.0}"
echo "  OpenAI API: http://localhost:${OPENCLAW_GATEWAY_PORT:-18789}/v1/chat/completions"
echo ""
exec openclaw gateway start --foreground
