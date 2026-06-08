# ESP32-S3 AI Assistant — Pcbfun 2.8" TFT Touch

Firmware, server, and web flash tools for the **Pcbfun ESP32-S3 2.8" TFT Touch** board
(aka XiaoP STEM / ES3C28P), integrated with **Xiaozhi AI** and **OpenClaw** gateway.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Docker Compose Stack                                                │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Xiaozhi Server   │  │ 智控台       │  │ OpenClaw Gateway       │  │
│  │ WS  :8000        │  │ Web :8002    │  │ AI  :18789             │  │
│  │ OTA :8003        │  │ (管理面板)   │  │ • OpenAI-compatible    │  │
│  │ • ASR + TTS      │──│ • Users      │  │ • WhatsApp/Telegram    │  │
│  │ • LLM routing    │  │ • Agents     │  │ • Claude/GPT/Qwen/... │  │
│  │ • MCP tools      │  │ • Devices    │  │                        │  │
│  └────────┬─────────┘  └──────┬───────┘  └────────────────────────┘  │
│           │            ┌──────┴────────┐                             │
│  ┌────────┴──────┐     │  MySQL + Redis│                             │
│  │ ESP32 devices │     └───────────────┘                             │
└──┼───────────────┼───────────────────────────────────────────────────┘
   │ WebSocket     │ USB
   ▼               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ESP32-S3 Board — Pcbfun 2.8" TFT Touch                             │
│  ILI9341 240×320 · ES8311 Audio · FT6336 Touch · WiFi+BLE           │
└──────────────────────────────────────────────────────────────────────┘
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
├── server/                            # Server infrastructure (Docker)
│   ├── docker-compose.yml             # Full stack: Xiaozhi + 智控台 + MySQL + Redis + OpenClaw
│   ├── .env.example                   # Environment variables template
│   ├── setup.sh                       # First-time setup script
│   ├── openclaw-setup.sh              # OpenClaw auto-setup script
│   └── xiaozhi-config.yaml            # Minimal (standalone) config template
├── firmware/                          # Custom board definition
│   ├── .github/workflows/             # CI/CD for firmware build
│   │   └── build-firmware.yml         # GitHub Actions: build + release
│   └── boards/pcbfun-tft280/          # Pcbfun 2.8" TFT board
│       ├── config.h                   # Pin mapping & hardware config
│       ├── config.json                # Build configuration
│       ├── pcbfun_tft280_board.cc     # Board initialization code
│       ├── ReadMe.md                  # Board-specific notes
│       └── mcp_tools_example.cc       # MCP custom tools examples
└── docs/                              # Documentation
    ├── openclaw-integration.md        # OpenClaw integration guide
    └── deployment-guide.md            # Full deployment guide (server + firmware + OTA)
```

## Quick Start

### 1. Deploy Server (Full Stack)

```bash
cd esp32/server

# Setup
cp .env.example .env
nano .env                  # set SERVER_IP, passwords
chmod +x setup.sh && ./setup.sh

# Start all services
docker compose up -d

# Wait ~30s for MySQL, then open 智控台
# http://<your-ip>:8002
```

**First-time setup:**
1. Register admin account at `http://<ip>:8002` (first user = superadmin)
2. Go to **参数管理** → copy **server.secret** value
3. Paste into `data/.config.yaml` → `manager-api.secret`
4. `docker compose restart xiaozhi-esp32-server`
5. Configure AI models in **模型配置** (add OpenClaw or other LLM)

See [Deployment Guide](docs/deployment-guide.md) for detailed instructions.

**Endpoints after startup:**
| Service | URL | Description |
|---|---|---|
| 智控台 | `http://<ip>:8002` | Web management panel |
| WebSocket | `ws://<ip>:8000/xiaozhi/v1/` | ESP32 device connections |
| OTA | `http://<ip>:8003/xiaozhi/ota/` | Firmware updates |
| OpenClaw | `http://<ip>:18789/v1/chat/completions` | AI gateway |

### 2. Build Firmware

**Option A — Local build:**
```bash
# Requires ESP-IDF v5.5 installed
git clone https://github.com/78/xiaozhi-esp32.git
cd xiaozhi-esp32
cp -r /path/to/esp32/firmware/boards/pcbfun-tft280 main/boards/
idf.py set-target esp32s3
idf.py -D BOARD=pcbfun-tft280 build
```

**Option B — Docker build (no ESP-IDF install needed):**
```bash
docker run --rm -v $(pwd):/project -w /project \
  espressif/idf:v5.5.2 bash -c \
  "source \$IDF_PATH/export.sh && \
   python scripts/release.py pcbfun-tft280 --name pcbfun-tft280"
```

**Option C — GitHub Actions CI/CD:**
Fork xiaozhi-esp32, copy `firmware/.github/workflows/build-firmware.yml`, push tag `v*` → auto release.

### 3. Flash Firmware

**Web Flash (recommended):** Copy .bin files to `web-flash/firmware/`, open page in Chrome, click flash.

**USB:** `esptool.py --chip esp32s3 write_flash 0x0 merged-binary.bin`

**OTA:** Board auto-checks server for updates after first flash.

### 4. Configure Board WiFi

1. Board boots → shows setup UI on LCD
2. **Hold BOOT button 3 seconds** → WiFi config mode
3. Connect to board's AP → configure your WiFi
4. Board connects to Xiaozhi server automatically

### 5. Deploy Features (3 Methods)

| Method | When to use | Reflash? |
|---|---|---|
| **OTA Update** | Major changes, new drivers, bug fixes | Yes (auto) |
| **MCP Tools** | Add AI-callable actions (LED, display, sensors) | Build once |
| **智控台** | Configure agents, models, manage devices | No |

See [mcp_tools_example.cc](firmware/boards/pcbfun-tft280/mcp_tools_example.cc) for MCP tool examples.

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
