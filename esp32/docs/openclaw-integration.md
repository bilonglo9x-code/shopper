# OpenClaw Integration Guide

## Overview

[OpenClaw](https://openclaw.ai) is an open-source AI assistant gateway that connects
multiple chat channels (WhatsApp, Telegram, Discord, Slack, Signal, etc.) to AI models.

In this setup, OpenClaw serves as the **AI backend** for the Xiaozhi ESP32 server,
providing:

- **Multi-channel support**: Send/receive messages from any connected chat app
- **AI agent**: Claude, GPT, or other LLM models
- **OpenAI-compatible API**: `/v1/chat/completions` endpoint
- **Memory & context**: Shared conversation history across channels
- **Tools/plugins**: Browser control, file access, custom skills

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  ESP32 Board │────►│ Xiaozhi      │────►│ OpenClaw     │
│  (voice+LCD) │ WS  │ Server       │ API │ Gateway      │
│              │◄────│ (ASR/TTS)    │◄────│ (AI/LLM)     │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                                    ┌───────────┼───────────┐
                                    ▼           ▼           ▼
                              ┌─────────┐ ┌─────────┐ ┌─────────┐
                              │Telegram │ │WhatsApp │ │Discord  │
                              │  Bot    │ │         │ │  Bot    │
                              └─────────┘ └─────────┘ └─────────┘
```

1. **User speaks** → ESP32 mic → Xiaozhi server ASR (speech-to-text)
2. **Text goes to LLM** → Xiaozhi server sends text to OpenClaw `/v1/chat/completions`
3. **AI responds** → OpenClaw returns AI response
4. **TTS plays** → Xiaozhi server TTS → audio to ESP32 speaker
5. **LCD shows** → Chat text displayed on 2.8" LCD

## Setup

### Prerequisites

- Docker and Docker Compose installed
- Server running (see main README)

### Step 1: Configure OpenClaw

The Docker Compose setup starts OpenClaw automatically. To configure it:

```bash
# Enter the OpenClaw container
docker exec -it openclaw-gateway sh

# Run interactive setup
openclaw onboard
# This will guide you through:
#   - Setting up AI provider (Claude/GPT API key)
#   - Creating a gateway token
#   - Basic configuration
```

### Step 2: Enable OpenAI-Compatible API

Already enabled in the Docker setup. Verify:

```bash
curl http://localhost:18789/v1/models \
  -H "Authorization: Bearer your-token"
```

Expected response: a list of available models.

### Step 3: Configure Xiaozhi Server

Edit `xiaozhi-data/.config.yaml`:

```yaml
llm:
  type: openai
  base_url: "http://openclaw:18789/v1"
  api_key: "your-openclaw-gateway-token"
  model: "openclaw"
```

Restart the Xiaozhi server:
```bash
docker compose restart xiaozhi-server
```

### Step 4: Add Chat Channels (Optional)

Connect external chat apps to OpenClaw:

```bash
docker exec -it openclaw-gateway sh

# Add Telegram bot
openclaw channel add telegram
# You'll need a Telegram Bot Token from @BotFather

# Add Discord bot
openclaw channel add discord
# You'll need a Discord Bot Token

# Add WhatsApp
openclaw channel add whatsapp
# Follow QR code pairing
```

### Step 5: Test the Integration

**Test via API:**
```bash
curl -X POST http://localhost:18789/v1/chat/completions \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openclaw",
    "messages": [
      {"role": "user", "content": "Hello, what can you do?"}
    ]
  }'
```

**Test via ESP32 board:**
1. Power on the board
2. Connect to WiFi
3. Tap the screen to start a voice conversation
4. Speak — the board should transcribe your voice, send it to the AI, and play the response

**Test via Telegram:**
1. Open your Telegram bot
2. Send a message — OpenClaw processes it and responds
3. The conversation context is shared (the bot "knows" what was said on the ESP32 too, if configured)

## Troubleshooting

### OpenClaw container won't start
```bash
docker compose logs openclaw
```
Common issues:
- Port 18789 already in use → change `OPENCLAW_PORT` in `.env`
- npm install fails → check network connectivity

### Xiaozhi can't reach OpenClaw
- Ensure both containers are on the same Docker network (`ai-network`)
- The Xiaozhi server should use `http://openclaw:18789/v1` as `base_url` (Docker DNS)
- Test from Xiaozhi container: `docker exec xiaozhi-server curl http://openclaw:18789/v1/models`

### AI responses are empty
- Check OpenClaw has an AI provider configured: `docker exec openclaw-gateway openclaw config show`
- Verify API key is set for your chosen provider

## Advanced: MCP Protocol

Xiaozhi firmware supports MCP (Model Context Protocol) for device control.
You can register custom "tools" on the ESP32 that the AI can call:

```cpp
// In pcbfun_tft280_board.cc → InitializeTools()
void InitializeTools() {
    auto& mcp_server = McpServer::GetInstance();

    // Register a tool that the AI can call to control the display
    mcp_server.AddTool("display.show_text", "Show text on LCD",
        PropertyList({{"text", "string", "Text to display"}}),
        [this](const PropertyList& props) -> ReturnValue {
            auto text = props.GetString("text");
            display_->ShowNotification(text);
            return true;
        });
}
```

This allows the AI (via OpenClaw) to trigger actions on the physical device.
