# Pcbfun ESP32-S3 2.8" TFT Touch Board

Custom board definition for the **Pcbfun / XiaoP STEM ESP32-S3 2.8" TFT Touch** board,
designed for the [Xiaozhi ESP32 AI](https://github.com/78/xiaozhi-esp32) firmware.

## Hardware

- **MCU**: ESP32-S3 N16R8 (16MB Flash, 8MB PSRAM)
- **Display**: 2.8" IPS ILI9341V, 240×320, SPI
- **Touch**: FT6336 Capacitive, I2C (addr 0x38)
- **Audio**: ES8311 codec + built-in mic + speaker
- **Battery**: Charging management, ADC on GPIO9

## Usage

Copy this entire directory into the Xiaozhi firmware `main/boards/` folder:

```bash
git clone https://github.com/78/xiaozhi-esp32.git
cp -r pcbfun-tft280 xiaozhi-esp32/main/boards/

cd xiaozhi-esp32
idf.py set-target esp32s3
idf.py -D BOARD=pcbfun-tft280 build
idf.py -p /dev/ttyUSB0 flash monitor
```

## Reference

Based on the [Freenove ESP32-S3 Display 2.8" LCD](https://github.com/78/xiaozhi-esp32/tree/main/main/boards/freenove-esp32s3-display-2.8-lcd)
board definition, which shares nearly identical hardware. Key differences:

- Touch RST pin: GPIO18 (Pcbfun) — Freenove doesn't use a touch reset pin
- Touch INT pin: GPIO17 (Pcbfun) — available for interrupt-driven touch
- Touch controller initialization includes hardware reset sequence

## Pin Notes

The I2C bus is shared between ES8311 audio codec and FT6336 touch controller:
- SDA = GPIO16
- SCL = GPIO15

The I2S audio pins (MCLK, BCLK, WS, DIN, DOUT) should be verified against your
specific board revision. The values in config.h are based on the Freenove reference.
If audio doesn't work, check the schematic from [xpstem.com](https://www.xpstem.com/product/board-esp32s3-tft280/guide).
