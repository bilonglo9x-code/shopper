# Deployment Guide — ESP32-S3 AI Assistant

Hướng dẫn triển khai đầy đủ: Server + Firmware build + OTA + 智控台

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Docker Compose Stack                                                │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ xiaozhi-server   │  │ 智控台       │  │ OpenClaw Gateway       │  │
│  │ WS  :8000        │  │ Web :8002    │  │ AI  :18789             │  │
│  │ OTA :8003        │  │ (管理面板)   │  │ • OpenAI-compatible    │  │
│  │ • ASR (voice→txt)│  │ • Users      │  │ • Multi-channel chat   │  │
│  │ • TTS (txt→voice)│  │ • Agents     │  │ • Claude/GPT/Qwen/...  │  │
│  │ • LLM routing    │  │ • Devices    │  │                        │  │
│  │ • MCP tools      │  │ • Models     │  │                        │  │
│  └────────┬─────────┘  └──────┬───────┘  └────────────────────────┘  │
│           │                   │                                      │
│  ┌────────┴───────┐  ┌───────┴────────┐                              │
│  │ MySQL 8.0      │  │ Redis 8.0      │                              │
│  │ (users, config)│  │ (sessions)     │                              │
│  └────────────────┘  └────────────────┘                              │
└──────────────────────────────────────────────────────────────────────┘
         │ WebSocket (WiFi)
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ESP32-S3 Board (Pcbfun 2.8" TFT Touch)                             │
│  Xiaozhi firmware → voice AI + LCD + touch + OTA + MCP tools         │
└──────────────────────────────────────────────────────────────────────┘
```

## Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB (all API) | 8 GB (local ASR) |
| Disk | 20 GB | 50 GB |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 |
| Docker | 24+ | 27+ |
| Network | LAN IP (local) | Static public IP (VPS) |

## Part 1: Server Deployment

### Step 1 — Clone & Setup

```bash
# Clone your repo
git clone https://github.com/bilonglo9x-code/shopper.git
cd shopper/esp32/server

# Create .env from template
cp .env.example .env

# Edit .env — set your IP and passwords
nano .env
```

Key `.env` settings:
```bash
SERVER_IP=192.168.1.100        # Your actual LAN/public IP
MYSQL_ROOT_PASSWORD=your-pass  # Change from default!
OPENCLAW_PASSWORD=your-token   # OpenClaw gateway token
```

### Step 2 — Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

This creates:
- `data/` — Xiaozhi server config directory
- `data/.config.yaml` — Server configuration (API mode)
- `mysql/data/` — Database storage
- `uploadfile/` — File uploads directory
- `openclaw-data/` — OpenClaw state

### Step 3 — Start Services

```bash
docker compose up -d

# Watch logs (wait for MySQL health check ~30s)
docker compose logs -f
```

### Step 4 — Configure 智控台

1. Open browser: `http://<your-ip>:8002`
2. **Register first user** — this becomes the **superadmin**
3. Login as superadmin
4. Go to **参数管理** (Parameter Management)
5. Find **server.secret** → copy the **参数值** (parameter value)
6. Edit `data/.config.yaml`:
   ```yaml
   manager-api:
     url: http://xiaozhi-esp32-server-web:8002/xiaozhi
     secret: <paste server.secret here>
   ```
7. Restart server:
   ```bash
   docker compose restart xiaozhi-esp32-server
   ```

### Step 5 — Configure AI Models (via 智控台)

1. In 智控台, go to **模型配置** (Model Configuration)
2. Left sidebar → **大语言模型** (LLM)
3. Add OpenClaw as provider:
   - Name: `OpenClaw`
   - Type: `openai`
   - API URL: `http://openclaw:18789/v1`
   - API Key: your OpenClaw gateway token
   - Model: `openclaw`
4. Left sidebar → **语音合成** (TTS)
   - Use EdgeTTS (free): voice `vi-VN-HoaiMyNeural` for Vietnamese
5. Left sidebar → **语音识别** (ASR)
   - Use Sherpa ONNX (built-in) or configure external API

### Step 6 — Configure OpenClaw

```bash
# Enter the container
docker exec -it openclaw-gateway sh

# Run setup wizard
openclaw onboard
# Follow prompts: set AI provider (Claude/GPT API key)

# Add chat channels (optional)
openclaw channel add telegram    # needs Telegram Bot Token
openclaw channel add discord     # needs Discord Bot Token
```

### Verify Services

```bash
# All containers running?
docker compose ps

# WebSocket alive?
curl -i http://localhost:8000/xiaozhi/v1/

# OTA endpoint?
curl http://localhost:8003/xiaozhi/ota/

# 智控台?
curl -s http://localhost:8002 | head -5

# OpenClaw API?
curl http://localhost:18789/v1/models -H "Authorization: Bearer your-token"
```

---

## Part 2: Firmware Build

### Option A — Local Build (trên máy tính)

```bash
# 1. Install ESP-IDF v5.5
git clone -b v5.5.2 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && ./install.sh esp32s3
source export.sh
cd ..

# 2. Clone Xiaozhi firmware
git clone https://github.com/78/xiaozhi-esp32.git
cd xiaozhi-esp32

# 3. Copy custom board
cp -r /path/to/shopper/esp32/firmware/boards/pcbfun-tft280 main/boards/

# 4. Configure OTA URL (point to your server)
# Edit main/Kconfig.projbuild:
#   CONFIG_OTA_URL="http://<your-server-ip>:8003/xiaozhi/ota/"

# 5. Build
idf.py set-target esp32s3
idf.py -D BOARD=pcbfun-tft280 build

# 6. Output files:
#   build/merged-binary.bin          ← single file (flash at 0x0)
#   build/bootloader/bootloader.bin  ← web flash parts
#   build/partition_table/partition-table.bin
#   build/ota_data_initial.bin
#   build/xiaozhi.bin
```

### Option B — GitHub Actions CI/CD (tự động)

1. Fork `https://github.com/78/xiaozhi-esp32` to your account
2. Copy board config:
   ```bash
   cp -r esp32/firmware/boards/pcbfun-tft280 main/boards/
   ```
3. Copy workflow:
   ```bash
   cp esp32/firmware/.github/workflows/build-firmware.yml .github/workflows/
   ```
4. Push to main → firmware builds automatically
5. Create tag `v1.0.0` → GitHub Release with .bin files

### Option C — Docker Build (không cần cài ESP-IDF)

```bash
docker run --rm -v $(pwd):/project -w /project \
  espressif/idf:v5.5.2 bash -c \
  "source \$IDF_PATH/export.sh && \
   python scripts/release.py pcbfun-tft280 --name pcbfun-tft280"
```

---

## Part 3: Flash Firmware

### Method 1 — Web Flash (Chrome, recommended)

1. Copy .bin files to `web-flash/firmware/`:
   ```
   bootloader.bin
   partition-table.bin
   ota_data_initial.bin
   firmware.bin (= xiaozhi.bin)
   ```
2. Open web flash page in Chrome/Edge
3. Connect board via USB-C
4. Click "Kết nối & Flash"

### Method 2 — USB Command Line

```bash
# Single merged binary
esptool.py --chip esp32s3 --port /dev/ttyUSB0 \
  write_flash 0x0 merged-binary.bin

# Or separate parts
esptool.py --chip esp32s3 --port /dev/ttyUSB0 \
  write_flash 0x0 bootloader.bin \
  0x8000 partition-table.bin \
  0xd000 ota_data_initial.bin \
  0x20000 xiaozhi.bin
```

### Method 3 — OTA Update (after first flash)

Board automatically checks OTA endpoint on boot:
```
GET http://<server>:8003/xiaozhi/ota/
→ Response: { "version": "1.1.0", "url": "https://..." }
→ Board downloads & flashes new firmware
→ Auto reboot
```

You can trigger OTA from 智控台:
1. Upload firmware .bin in 智控台 → **固件管理** (Firmware Management)
2. Assign firmware to devices
3. Devices auto-update on next connection

---

## Part 4: Feature Deployment (3 Methods)

### Method 1 — OTA Firmware Update
**When**: Major changes, new drivers, bug fixes
**How**: Build new firmware → upload to server → devices auto-update

### Method 2 — MCP Tools (no reflash needed)
**When**: Add AI-callable device actions (LED, display, sensors)
**How**: Register tools in firmware → AI discovers them automatically

See `firmware/boards/pcbfun-tft280/mcp_tools_example.cc` for examples:
- `lamp.toggle` — LED control
- `display.show_text` — Show text on LCD
- `device.battery_level` — Report battery
- `gpio.set` — Generic GPIO control
- `device.set_timer` — Set alarms/timers
- `display.brightness` — Adjust screen brightness

### Method 3 — 智控台 Management
**When**: Configure AI agents, manage devices, update models
**How**: Web UI at `http://<ip>:8002`

Features:
- **智能体管理** — Create/manage AI agents with different personalities
- **模型配置** — Switch LLM/ASR/TTS providers
- **设备管理** — View connected devices, push commands
- **固件管理** — Upload & distribute firmware OTA
- **用户管理** — Multi-user access control
- **参数管理** — System configuration
- **MCP指令下发** — Send MCP commands to devices from web panel

---

## VPS Deployment Notes

For production VPS deployment, add these to your server:

```bash
# Firewall (allow required ports)
sudo ufw allow 8000/tcp   # WebSocket
sudo ufw allow 8002/tcp   # 智控台
sudo ufw allow 8003/tcp   # OTA
sudo ufw allow 18789/tcp  # OpenClaw (optional, if external access needed)

# SSL/HTTPS (recommended for production)
# Use nginx reverse proxy + Let's Encrypt
sudo apt install nginx certbot python3-certbot-nginx
```

Example nginx config (`/etc/nginx/sites-available/xiaozhi`):
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 智控台
    location / {
        proxy_pass http://127.0.0.1:8002;
    }

    # WebSocket
    location /xiaozhi/v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # OTA
    location /xiaozhi/ota/ {
        proxy_pass http://127.0.0.1:8003;
    }
}
```

---

## Troubleshooting

### MySQL won't start
```bash
docker compose logs xiaozhi-esp32-server-db
# Common: permission issues on mysql/data
sudo chown -R 999:999 mysql/data
```

### 智控台 shows blank page
- Wait 30-60s after first start (Java Spring Boot startup)
- Check: `docker compose logs xiaozhi-esp32-server-web`

### Server can't connect to 智控台
- Verify `server.secret` in `data/.config.yaml` matches 智控台 → 参数管理
- URL must be `http://xiaozhi-esp32-server-web:8002/xiaozhi` (Docker DNS)

### Board can't connect to server
- Verify WiFi connected
- Check WebSocket URL: `ws://<server-ip>:8000/xiaozhi/v1/`
- Test from same network: `curl http://<server-ip>:8000`

### OTA not working
- Check OTA URL in firmware Kconfig matches your server
- Test: `curl http://<server-ip>:8003/xiaozhi/ota/`
- Upload firmware in 智控台 → 固件管理

### OpenClaw errors
```bash
docker compose logs openclaw
docker exec -it openclaw-gateway openclaw config show
```
