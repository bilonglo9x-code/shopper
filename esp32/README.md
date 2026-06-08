# ESP32-S3 AI Assistant — Pcbfun 2.8" TFT Touch

Firmware, server, and web flash tools for the **Pcbfun ESP32-S3 2.8" TFT Touch** board
(aka XiaoP STEM / ES3C28P), integrated with **Xiaozhi AI** and **OpenClaw** gateway.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Server (Docker)                          │
│                                                              │
│  ┌─────────────────────┐   ┌──────────────────────────────┐  │
│  │ Xiaozhi Server      │   │ OpenClaw Gateway             │  │
│  │                     │   │                              │  │
│  │ • WS :8000 (device) │──►│ • /v1/chat/completions      │  │
│  │ • HTTP :8003 (OTA)  │   │ • WhatsApp/Telegram/Discord  │  │
│  │ • ASR + TTS         │   │ • AI agent (Claude/GPT/...)  │  │
│  └──────────┬──────────┘   └──────────────────────────────┘  │
└─────────────┼────────────────────────────────────────────────┘
              │ WebSocket (WiFi)
              ▼
┌──────────────────────────────────────────────────────────────┐
│  ESP32-S3 Board — Pcbfun 2.8" TFT Touch                     │
│  ILI9341 240×320 · ES8311 Audio · FT6336 Touch · WiFi+BLE   │
└──────────────────────────────────────────────────────────────┘
              ▲
              │ USB (first flash)
┌─────────────┴───────────────┐
│  Web Flash Page             │
│  (ESP Web Tools / Chrome)   │
└─────────────────────────────┘
```

## Board Specifications

| Component | Detail |
|---|---|
| MCU | ESP32-S3 N16R8 (240 MHz dual-core, 16 MB Flash, 8 MB PSRAM) |
| Display | 2.8" IPS ILI9341V, 240×320, SPI interface |
| Touch | Capacitive FT6336, I2C (addr 0x38) |
| Audio | ES8311 codec, built-in mic + speaker output |
| Battery | Charging management, ADC monitoring (GPIO9) |
| Storage | MicroSD slot |
| Connectivity | WiFi 2.4 GHz 802.11 b/g/n + Bluetooth BLE 5.0 |

### Pin Mapping

| Function | GPIO | Notes |
|---|---|---|
| LCD CS | IO10 | SPI chip select |
| LCD DC | IO46 | Data/Command |
| LCD CLK | IO12 | SPI clock |
| LCD MOSI | IO11 | SPI data |
| LCD MISO | IO13 | SPI read |
| LCD Backlight | IO45 | HIGH = on |
| Touch SDA | IO16 | I2C (shared with ES8311) |
| Touch SCL | IO15 | I2C (shared with ES8311) |
| Touch RST | IO18 | Reset |
| Touch INT | IO17 | Interrupt |
| Battery ADC | IO9 | ADC1_CH8 |
| Boot Button | IO0 | — |
| LED | IO48 | WS2812 or single LED |

## Directory Structure

```
esp32/
├── README.md                          # This file
├── web-flash/                         # Browser-based firmware installer
│   ├── index.html                     # Flash page (ESP Web Tools)
│   ├── manifest.json                  # Firmware manifest
│   └── firmware/                      # Place compiled .bin files here
├── server/                            # Server infrastructure
│   ├── docker-compose.yml             # Xiaozhi + OpenClaw containers
│   ├── .env.example                   # Environment variables template
│   ├── openclaw-setup.sh              # OpenClaw auto-setup script
│   └── xiaozhi-config.yaml            # Xiaozhi server config template
├── firmware/                          # Custom board definition
│   └── boards/pcbfun-tft280/          # Pcbfun 2.8" TFT board
│       ├── config.h                   # Pin mapping & hardware config
│       ├── config.json                # Build configuration
│       └── pcbfun_tft280_board.cc     # Board initialization code
└── docs/                              # Additional documentation
    └── openclaw-integration.md        # OpenClaw integration guide
```

## Quick Start

### 1. Start the Server

```bash
cd esp32/server

# Copy and edit configuration
cp .env.example .env
# Edit .env: set your API keys and server IP

# Create Xiaozhi data directory with config
mkdir -p xiaozhi-data
cp xiaozhi-config.yaml xiaozhi-data/.config.yaml
# Edit .config.yaml: replace ${SERVER_IP} with your actual IP

# Start services
docker compose up -d

# Verify
docker compose logs -f
```

**Endpoints after startup:**
- Xiaozhi WebSocket: `ws://<your-ip>:8000/xiaozhi/v1/`
- Xiaozhi OTA: `http://<your-ip>:8003/xiaozhi/ota/`
- OpenClaw API: `http://<your-ip>:18789/v1/chat/completions`

### 2. Build Firmware

```bash
# Clone Xiaozhi firmware
git clone https://github.com/78/xiaozhi-esp32.git
cd xiaozhi-esp32

# Copy custom board definition
cp -r /path/to/esp32/firmware/boards/pcbfun-tft280 main/boards/

# Setup ESP-IDF v5.5 (if not installed)
# See: https://docs.espressif.com/projects/esp-idf/en/v5.5.2/esp32s3/get-started/

# Build
idf.py set-target esp32s3
idf.py -D BOARD=pcbfun-tft280 build
```

### 3. Flash via Web

**Option A — Web Flash (recommended for first time):**

1. Copy compiled `.bin` files to `esp32/web-flash/firmware/`:
   - `bootloader.bin`
   - `partition-table.bin`
   - `ota_data_initial.bin`
   - `firmware.bin`
2. Serve the `web-flash/` directory over HTTPS (GitHub Pages, Vercel, etc.)
3. Open in Chrome → click "Kết nối & Flash" → select USB port

**Option B — Command line:**
```bash
idf.py -p /dev/ttyUSB0 flash monitor
```

**Option C — OTA update (after first flash):**

The firmware will automatically check for updates from the OTA endpoint configured in `.config.yaml`.

### 4. Configure WiFi on Board

After flashing:
1. The board boots and shows the setup UI on LCD
2. **Press and hold BOOT button for 3 seconds** to enter WiFi config mode
3. Connect to the board's WiFi AP and configure your home WiFi
4. The board connects to your Xiaozhi server automatically

### 5. Setup OpenClaw (Optional)

OpenClaw provides multi-channel AI chat (WhatsApp, Telegram, Discord, etc.).

```bash
# On the OpenClaw container (or your machine)
docker exec -it openclaw-gateway sh

# Run interactive setup
openclaw onboard

# Pair a chat channel (e.g., Telegram)
openclaw channel add telegram
# Follow the prompts to connect your Telegram bot
```

See [OpenClaw Integration Guide](docs/openclaw-integration.md) for detailed setup.

## OpenClaw Integration

OpenClaw serves as the AI backend for the Xiaozhi server. The integration works via
OpenAI-compatible API:

```
ESP32 Board  ──WebSocket──►  Xiaozhi Server  ──HTTP/v1──►  OpenClaw Gateway
  (voice/LCD)                  (ASR/TTS)                    (LLM/channels)
```

- **Voice input** on the board → Xiaozhi ASR → text → OpenClaw LLM → response text → Xiaozhi TTS → audio output
- **Chat messages** from WhatsApp/Telegram → OpenClaw → shared conversation context
- **Display commands** → OpenClaw can trigger display updates via MCP tools

## Touch Gestures

| Gesture | Action |
|---|---|
| Single tap | Toggle chat state (start/stop listening) |
| Double tap | Start voice listening |
| Long press (3s) | Enter WiFi config mode |

## References

- [Xiaozhi ESP32 Firmware](https://github.com/78/xiaozhi-esp32) — Base firmware (27K+ stars)
- [Xiaozhi ESP32 Server](https://github.com/xinnan-tech/xiaozhi-esp32-server) — Backend server
- [OpenClaw](https://openclaw.ai) — AI assistant gateway
- [ESP Web Tools](https://github.com/esphome/esp-web-tools) — Browser-based flashing
- [Board Docs (XiaoP STEM)](https://www.xpstem.com/product/board-esp32s3-tft280/guide) — Hardware reference
- [ESP-IDF Programming Guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/) — Development framework
