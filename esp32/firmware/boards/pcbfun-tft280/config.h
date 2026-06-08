/**
 * Board configuration for Pcbfun ESP32-S3 2.8" TFT Touch
 * (aka XiaoP STEM / ES3C28P board)
 *
 * Hardware:
 *   - MCU: ESP32-S3 N16R8 (16MB Flash, 8MB PSRAM)
 *   - Display: 2.8" IPS ILI9341V, 240x320, SPI
 *   - Touch: Capacitive FT6336, I2C
 *   - Audio: ES8311 codec + mic + speaker
 *   - Battery: Charging management, ADC
 *   - Storage: MicroSD slot
 *
 * Pin source: https://www.xpstem.com/product/board-esp32s3-tft280/guide
 */

#ifndef _BOARD_CONFIG_H_
#define _BOARD_CONFIG_H_

#include <driver/gpio.h>

/* ── Audio ─────────────────────────────────────────────────── */

#define AUDIO_INPUT_SAMPLE_RATE  24000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000

// I2S pins — ES8311 codec (confirm with your board's schematic)
#define AUDIO_I2S_GPIO_MCLK      GPIO_NUM_4
#define AUDIO_I2S_GPIO_BCLK      GPIO_NUM_5
#define AUDIO_I2S_GPIO_DIN       GPIO_NUM_6
#define AUDIO_I2S_GPIO_WS        GPIO_NUM_7
#define AUDIO_I2S_GPIO_DOUT      GPIO_NUM_8
#define AUDIO_CODEC_PA_PIN       GPIO_NUM_1

// I2C bus for ES8311 + FT6336 touch (shared bus)
#define AUDIO_CODEC_I2C_NUM      I2C_NUM_0
#define AUDIO_CODEC_I2C_SDA_PIN  GPIO_NUM_16
#define AUDIO_CODEC_I2C_SCL_PIN  GPIO_NUM_15
#define AUDIO_CODEC_ES8311_ADDR  ES8311_CODEC_DEFAULT_ADDR

/* ── Buttons & LED ─────────────────────────────────────────── */

#define BOOT_BUTTON_GPIO         GPIO_NUM_0
#define BUILTIN_LED_GPIO         GPIO_NUM_48
#define TOUCH_BUTTON_GPIO        GPIO_NUM_NC
#define VOLUME_UP_BUTTON_GPIO    GPIO_NUM_NC
#define VOLUME_DOWN_BUTTON_GPIO  GPIO_NUM_NC

/* ── Display — ILI9341V 240x320 SPI ───────────────────────── */

#define DISPLAY_BACKLIGHT_PIN    GPIO_NUM_45
#define DISPLAY_RST_PIN          GPIO_NUM_NC   // shared with chip EN
#define DISPLAY_SCK_PIN          GPIO_NUM_12
#define DISPLAY_DC_PIN           GPIO_NUM_46
#define DISPLAY_CS_PIN           GPIO_NUM_10
#define DISPLAY_MOSI_PIN         GPIO_NUM_11
#define DISPLAY_MIS0_PIN         GPIO_NUM_13
#define DISPLAY_SPI_SCLK_HZ     (40 * 1000 * 1000)

#define LCD_SPI_HOST             SPI3_HOST

#define LCD_TYPE_ILI9341_SERIAL
#define DISPLAY_WIDTH            240
#define DISPLAY_HEIGHT           320
#define DISPLAY_MIRROR_X         false
#define DISPLAY_MIRROR_Y         false
#define DISPLAY_SWAP_XY          false
#define DISPLAY_INVERT_COLOR     true
#define DISPLAY_RGB_ORDER        LCD_RGB_ELEMENT_ORDER_BGR
#define DISPLAY_OFFSET_X         0
#define DISPLAY_OFFSET_Y         0
#define DISPLAY_BACKLIGHT_OUTPUT_INVERT false
#define DISPLAY_SPI_MODE         0

/* ── Touch — FT6336 Capacitive (I2C addr 0x38) ────────────── */

#define TOUCH_I2C_ADDR           0x38
#define TOUCH_RST_PIN            GPIO_NUM_18
#define TOUCH_INT_PIN            GPIO_NUM_17

/* ── Battery ───────────────────────────────────────────────── */

#define BATTERY_ADC_PIN          GPIO_NUM_9
#define ADC_BATTERY_CHANNEL      ADC_CHANNEL_8  // GPIO9 = ADC1_CH8

#endif // _BOARD_CONFIG_H_
