/**
 * MCP Custom Tools Example — Pcbfun 2.8" TFT Touch
 *
 * This file shows how to register custom MCP tools that AI can invoke.
 * MCP tools let you add device capabilities WITHOUT reflashing firmware.
 *
 * The AI (via OpenClaw/Xiaozhi) can call these tools based on user commands:
 *   "Turn on the LED" → AI calls lamp.toggle {state: true}
 *   "Show weather"    → AI calls display.show_text {text: "Sunny 28°C"}
 *   "What's the temp?" → AI calls sensor.read_temperature → returns value
 *
 * How to use:
 *   1. Copy relevant tool registrations into your board's InitializeMcpTools()
 *   2. Build & flash firmware
 *   3. The AI automatically discovers registered tools via MCP protocol
 *
 * Reference: https://github.com/78/xiaozhi-esp32 (MCP implementation)
 */

#include <driver/gpio.h>
#include "board.h"  // Board-specific definitions

// ── LED Control Tool ───────────────────────────────────────────
// Allows AI to toggle the onboard LED via voice command.
//
// Usage: "Hey Xiaozhi, turn on the light"
//   → AI calls: lamp.toggle { "state": true }
//   → Board sets GPIO48 HIGH → LED on
//   → AI responds: "Light is now on"
//
// Registration example (add to your board's InitializeMcpTools):
//
//   auto& mcp = McpServer::GetInstance();
//   mcp.AddTool("lamp.toggle", "Toggle the onboard LED",
//       PropertyList({
//           {"state", "boolean", "true=on, false=off"}
//       }),
//       [](const PropertyList& props) -> ReturnValue {
//           bool state = props.GetBool("state");
//           gpio_set_level(BUILTIN_LED_GPIO, state ? 1 : 0);
//           return state ? "LED turned on" : "LED turned off";
//       });

// ── Display Text Tool ─────────────────────────────────────────
// Allows AI to show custom text/notifications on the LCD.
//
// Usage: "Show me a reminder to drink water"
//   → AI calls: display.show_text { "text": "Drink water!", "duration": 5 }
//
// Registration:
//
//   mcp.AddTool("display.show_text", "Show text on LCD display",
//       PropertyList({
//           {"text", "string", "Text to display on screen"},
//           {"duration", "number", "Display duration in seconds (default 5)"}
//       }),
//       [this](const PropertyList& props) -> ReturnValue {
//           auto text = props.GetString("text");
//           int duration = props.GetInt("duration", 5);
//           display_->ShowNotification(text, duration * 1000);
//           return "Displayed: " + text;
//       });

// ── Battery Status Tool ───────────────────────────────────────
// Reports current battery level to the AI.
//
// Usage: "What's the battery level?"
//   → AI calls: device.battery_level {}
//   → Board reads ADC → returns percentage
//
// Registration:
//
//   mcp.AddTool("device.battery_level", "Get current battery percentage",
//       PropertyList({}),
//       [this](const PropertyList& props) -> ReturnValue {
//           int level = GetBatteryLevel();
//           return std::to_string(level) + "%";
//       });

// ── GPIO Control Tool (Generic) ──────────────────────────────
// Allows AI to control arbitrary GPIO pins.
// WARNING: Restrict to safe pins only in production!
//
// Usage: "Set pin 2 high" or "Turn on the relay"
//
// Registration:
//
//   mcp.AddTool("gpio.set", "Set a GPIO pin high or low",
//       PropertyList({
//           {"pin", "number", "GPIO pin number"},
//           {"level", "boolean", "true=HIGH, false=LOW"}
//       }),
//       [](const PropertyList& props) -> ReturnValue {
//           int pin = props.GetInt("pin");
//           bool level = props.GetBool("level");
//           // Safety: only allow specific pins
//           if (pin != 2 && pin != 48) {
//               return ReturnValue::Error("Pin not allowed");
//           }
//           gpio_set_level((gpio_num_t)pin, level ? 1 : 0);
//           return "GPIO" + std::to_string(pin) + " set to " +
//                  (level ? "HIGH" : "LOW");
//       });

// ── Timer/Alarm Tool ──────────────────────────────────────────
// Allows AI to set a timer that plays a sound when done.
//
// Usage: "Set a timer for 5 minutes"
//   → AI calls: device.set_timer { "seconds": 300, "label": "Tea" }
//
// Registration:
//
//   mcp.AddTool("device.set_timer", "Set a countdown timer",
//       PropertyList({
//           {"seconds", "number", "Timer duration in seconds"},
//           {"label", "string", "Timer label (optional)"}
//       }),
//       [this](const PropertyList& props) -> ReturnValue {
//           int seconds = props.GetInt("seconds");
//           auto label = props.GetString("label", "Timer");
//           // Start timer task (implementation depends on your RTOS setup)
//           StartTimerTask(seconds, label);
//           return "Timer set: " + label + " (" +
//                  std::to_string(seconds) + "s)";
//       });

// ── Screen Brightness Tool ────────────────────────────────────
// Adjusts LCD backlight brightness.
//
// Usage: "Dim the screen" or "Set brightness to 50%"
//
// Registration:
//
//   mcp.AddTool("display.brightness", "Adjust screen brightness",
//       PropertyList({
//           {"level", "number", "Brightness 0-100 (percent)"}
//       }),
//       [](const PropertyList& props) -> ReturnValue {
//           int level = props.GetInt("level");
//           level = std::clamp(level, 0, 100);
//           // Map 0-100% to PWM duty cycle
//           int duty = (level * 255) / 100;
//           // Assuming LEDC channel 0 for backlight
//           ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
//           ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
//           return "Brightness set to " + std::to_string(level) + "%";
//       });
