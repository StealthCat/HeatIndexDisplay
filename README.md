# HeatIndexDisplay

ESP32-S3 apparent-temperature displays for personal weather-station data from Ambient Weather or Weather Underground.

The firmware automatically shows **Heat Index** in hot conditions and **Wind Chill** when NWS wind-chill conditions apply. It supports two production targets:

- **LILYGO T-Display S3** — 170x320 ST7789, native LovyanGFX Parallel8 driver
- **Waveshare ESP32-S3 Touch LCD 2.8** — 240x320 ST7789 SPI

## Display mockup

The production UI is designed to match the following Heat Index and Wind Chill layouts on both supported displays:

![HeatIndexDisplay production mockup showing T-Display S3 and Waveshare 2.8-inch displays in Heat Index and Wind Chill modes](docs/weather_dashboard_device_comparison.webp)

## Current release: V7.8.1

V7.8.1 keeps the approved production layouts and provider selection while making live provider summaries more reliable. Ambient widens its same-time-yesterday REST window. Weather Underground now prefers recent 7-day hourly REST observations for Today High/Low and From Yesterday, then falls back to recent 1-day and archived history products.

### Compile-time defaults

Each board project contains `include/compile_defaults.h`. You may bake in Wi-Fi plus Ambient Weather or Weather Underground credentials there. Those values seed NVS **only on a blank device**. After that, changes made in the `/config` web panel persist and override the compiled values across reboots. Factory Reset clears NVS and allows the compiled defaults to seed again.

The repository intentionally ships with all credential fields blank. **Do not commit real Wi-Fi passwords or weather API keys to this public repository.**

## Build

Open either board directory as a PlatformIO project, or run:

```bash
cd T-Display-S3
pio run
```

or:

```bash
cd Waveshare-ESP32-S3-Touch-LCD-2.8
pio run
```

For a clean Windows build, run the included `CLEAN_BUILD_WINDOWS.bat` from the selected board directory.

## Configuration

With no stored Wi-Fi configuration, the device starts a `HeatIndex-Setup-XXXX` access point. Connect to it and open `http://192.168.4.1/config`.

The configuration panel controls Wi-Fi, hostname, timezone, weather source, Ambient credentials/station MAC, Weather Underground API key/PWS Station ID, polling interval, and stale-data threshold. Saved secrets are not rendered back into the page.

## Production Release V7.5

The display iconography uses fixed RGB565 asset sprites in `include/ui_assets.h` to more closely match the approved mockup.

## Production Release V7.5.1

Restores the Waveshare `directionLongText()` helper accidentally removed during the V7.5 icon conversion and adds an explicit forward declaration. See `RELEASE_V7_5_1_DIRECTION_FIX.md`.


## Production Release V7.6

Both board projects are now split into normal `.cpp`/`.h` modules by functional area. See `ARCHITECTURE.md` and `RELEASE_V7_6_MODULAR_REFACTOR.md`.


## Production Release V7.7

Adds a web-selectable **Ambient Weather / Weather Underground** source. Weather Underground uses the official PWS current endpoint and per-day historical observations to preserve the existing display metrics. See `RELEASE_V7_7_WEATHER_SOURCES.md`.


## Production Release V7.8

Today High/Low and From Yesterday are fetched from the REST history API belonging to the selected weather source. Ambient uses explicit current and same-local-time-yesterday history queries. Weather Underground prefers the daily-summary REST endpoint for Today High/Low and uses all-history data for the same local time yesterday, with an all-history fallback for the current-day summary. See `RELEASE_V7_8_PROVIDER_REST_SUMMARY.md`.


## Production Release V7.8.1

Live Weather Underground summaries now prefer `/v2/pws/observations/hourly/7day`, use provider-local `obsTimeLocal` for today/yesterday matching, and fall back through `/observations/all/1day` and archived history. Ambient widens the same-time-yesterday REST window. See `RELEASE_V7_8_1_LIVE_PROVIDER_SUMMARY_FIX.md`.
