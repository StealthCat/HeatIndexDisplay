# HeatIndexDisplay

ESP32-S3 apparent-temperature displays for personal weather-station data from **Ambient Weather** or **Weather Underground**.

The firmware automatically displays **Heat Index** in hot conditions and **Wind Chill** when National Weather Service wind-chill conditions apply. Current conditions, historical comparisons, wind, and forecast information are presented in a compact dashboard designed for always-on weather displays.

## Branches

- **`main`** — stable production firmware for the LILYGO T-Display S3 and Waveshare 2.8-inch display.
- **`concept-1`** — adds the Waveshare 7C-BOX 800×480 Concept-1 display plus the desktop/browser emulator. Emulator documentation is consolidated into that branch's root `README.md`.

## Supported hardware

| Target | Resolution | Display / driver |
| --- | ---: | --- |
| LILYGO T-Display S3 | 170×320 | ST7789, LovyanGFX Parallel8 |
| Waveshare ESP32-S3 Touch LCD 2.8 | 240×320 | ST7789 SPI |

The `concept-1` branch additionally supports the Waveshare ESP32-S3 Touch LCD 7C-BOX at 800×480.

## Display

![HeatIndexDisplay production mockup showing T-Display S3 and Waveshare 2.8-inch displays](docs/weather_dashboard_device_comparison.webp)

The production UI includes:

- station name and date
- current apparent temperature with automatic Heat Index / Wind Chill mode
- air temperature, humidity, dew point, and From Yesterday
- wind speed, gust, maximum daily gust, and direction
- Today / Tomorrow forecast high and low
- updated time plus ONLINE / STALE status

## Weather calculations

Heat Index uses the NWS simple estimate and Rothfusz regression with the standard humidity adjustments. Wind Chill is used when temperature is 50°F or below and wind speed exceeds 3 mph. Dew point uses the Magnus approximation. Wind direction is rendered on a 16-point compass.

## Weather sources

The source is selectable from the device configuration page.

### Ambient Weather

Current conditions are obtained from the Ambient Weather API. REST history is used for observed daily summary values and the same-local-time-yesterday comparison.

### Weather Underground

Current conditions come from the Weather Underground PWS API. Historical data prefers recent hourly observations and falls back through recent one-day and archived history endpoints as needed.

### Forecast

The selected station's latitude and longitude are sent to Open-Meteo for a two-day daily forecast. The forecast card alternates between **Today** and **Tomorrow** every 30 seconds. Forecast data refreshes every 15 minutes after a successful fetch, with shorter retries until an initial forecast is available.

## Configuration

On a device with no stored Wi-Fi configuration, the firmware starts a `HeatIndex-Setup-XXXX` access point. Connect to it and open:

```text
http://192.168.4.1/config
```

The configuration panel controls:

- Wi-Fi SSID and password
- hostname
- timezone
- Ambient Weather or Weather Underground source
- Ambient API/application keys and station MAC
- Weather Underground API key and PWS station ID
- polling interval
- stale-data threshold

Saved secrets are not rendered back into the page.

### Compile-time defaults

Each board project contains `include/compile_defaults.h`. Wi-Fi and weather-provider defaults may be compiled into a device, but they seed NVS **only when NVS is blank**. Settings saved through `/config` persist across reboots and override compiled defaults. Factory Reset clears NVS so compiled defaults can seed again.

The public repository intentionally ships with credential fields blank. **Do not commit real Wi-Fi passwords or weather API keys.**

## Build

Each hardware directory is an independent PlatformIO project.

### LILYGO T-Display S3

```bash
cd T-Display-S3
pio run
```

### Waveshare 2.8-inch

```bash
cd Waveshare-ESP32-S3-Touch-LCD-2.8
pio run
```

For a clean Windows build, run the included `CLEAN_BUILD_WINDOWS.bat` from the selected board directory.

## Architecture

The firmware is split by functional area rather than concentrated in `main.cpp`. The major modules are:

- `app_controller` — application lifecycle and polling orchestration
- `app_state` — shared weather/configuration state
- `config_store` — persistent configuration
- `wifi_manager` — Wi-Fi and setup behavior
- `weather_source` — provider selection
- `ambient_weather` — Ambient Weather client and history handling
- `wunderground_weather` — Weather Underground client and fallback history handling
- `forecast_weather` — Open-Meteo forecast client
- `weather_math` — apparent temperature, dew point, risk, and direction calculations
- `display_ui` / `ui_state` / `ui_assets` — dashboard rendering and assets
- `web_ui` — configuration/status web interface

`src/main.cpp` remains intentionally small and hands control to the application modules.

## Release history

The former standalone release-note Markdown files have been consolidated here.

- **V7.4** — compile-time defaults for both production targets.
- **V7.5** — fixed RGB565 display asset sprites for closer mockup matching.
- **V7.5.1** — restored the Waveshare direction helper removed during the icon conversion.
- **V7.6** — modular refactor into functional `.cpp` / `.h` components.
- **V7.7** — selectable Ambient Weather and Weather Underground providers.
- **V7.8** — provider REST history for observed Today High/Low and From Yesterday.
- **V7.8.1** — stronger provider-local history matching and Weather Underground fallback behavior.
- **V7.9** — High/Low card switched to Open-Meteo Today/Tomorrow forecast data with 30-second alternation.
- **V7.10** — display hierarchy, typography, and scanability refinements.
- **V7.11.5** — production display refinements, aligned metric cards, improved bottom-row layout, and ONLINE/STALE footer treatment.
- **V7.11.6** — Waveshare apparent-temperature value/degree/F group alignment for three-digit values.

For the 800×480 Concept-1 display and emulator work, use the `concept-1` branch.

## CI

GitHub Actions builds the supported PlatformIO targets on pushes and pull requests. The Concept-1 branch also runs the emulator's unit-test suite and functional parity checks.

## License / use

This repository is intended for the HeatIndexDisplay firmware and its associated emulator. Review third-party board, graphics, weather-provider, and API terms for their respective licensing and usage requirements.
