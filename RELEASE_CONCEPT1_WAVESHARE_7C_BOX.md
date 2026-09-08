# Concept 1 — Waveshare ESP32-S3 Touch LCD 7C-BOX

Adds `Waveshare-ESP32-S3-Touch-LCD-7C-BOX` as a third production/CI target on the `concept-1` branch.

## Hardware target

- Waveshare ESP32-S3-Touch-LCD-7C-BOX
- 800x480 landscape LCD
- ST7262 RGB panel
- RGB565 / 16-bit RGB interface
- GT911 touch hardware is present but intentionally unused by HeatIndexDisplay
- 16 MHz pixel clock
- HSYNC: GPIO46, VSYNC: GPIO3, DE: GPIO5, PCLK: GPIO7
- R0-R4: GPIO1, GPIO2, GPIO42, GPIO41, GPIO40
- G0-G5: GPIO39, GPIO0, GPIO45, GPIO9, GPIO8, GPIO21
- B0-B4: GPIO14, GPIO38, GPIO18, GPIO17, GPIO10
- IO-expander/backlight I2C: SDA GPIO47, SCL GPIO48; expander address 0x24

The display is driven through Arduino_GFX's ESP32-S3 RGB-panel support. The target uses the Arduino-ESP32 3.3.5-compatible pioarduino PlatformIO package because the Waveshare 7C reference platform targets the Arduino 3.x / ESP-IDF 5.x RGB LCD stack.

## Layout port

The Waveshare 2.8-inch Concept 1 structure is retained rather than redesigned:

- station name upper-left
- date upper-right
- `CURRENT CONDITIONS` subtitle
- dynamic Heat Index / Wind Chill hero panel at left
- four stacked metric cards at right: Temp, Humidity, Dew Point, From Yesterday
- Wind, Direction, and Today/Tomorrow Forecast cards across the lower row
- Updated timestamp and ONLINE/STALE state in the footer

Coordinates, card sizes, icon scaling, and typography are enlarged for the 800x480 panel. Existing dynamic Heat Index and Wind Chill color palettes, centered risk labels, forecast alternation, historical comparison data, Ambient Weather / Weather Underground selection, setup AP, web configuration, and stale-data behavior are preserved.

## Build

```bash
cd Waveshare-ESP32-S3-Touch-LCD-7C-BOX
pio run
```

The repository CI matrix now compiles all three firmware targets.
