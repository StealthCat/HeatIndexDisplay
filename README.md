# HeatIndexDisplay

ESP32-S3 apparent-temperature displays for an Ambient Weather WS-5000 station.

The firmware automatically shows **Heat Index** in hot conditions and **Wind Chill** when NWS wind-chill conditions apply. It supports two production targets:

- **LILYGO T-Display S3** — 170x320 ST7789, native LovyanGFX Parallel8 driver
- **Waveshare ESP32-S3 Touch LCD 2.8** — 240x320 ST7789 SPI

## Current release: V7.4

V7.4 includes the final approved display layouts, Ambient current/history polling, From Yesterday and Today's High/Low, first-boot setup AP, persistent web configuration, and optional compile-time Wi-Fi/Ambient defaults.

### Compile-time defaults

Each board project contains `include/compile_defaults.h`. You may bake in Wi-Fi and AmbientWeather.net credentials there. Those values seed NVS **only on a blank device**. After that, changes made in the `/config` web panel persist and override the compiled values across reboots. Factory Reset clears NVS and allows the compiled defaults to seed again.

The repository intentionally ships with all credential fields blank. **Do not commit real Wi-Fi passwords or Ambient API keys to this public repository.**

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

The configuration panel controls Wi-Fi, hostname, timezone, Ambient Application Key, Ambient API Key, station MAC, polling interval, and stale-data threshold. Saved secrets are not rendered back into the page.

See [RELEASE_V7_4.md](RELEASE_V7_4.md) for release details.
