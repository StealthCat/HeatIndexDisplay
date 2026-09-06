# Production Release V7.4

V7.4 adds optional compile-time first-boot defaults for Wi-Fi and AmbientWeather.net while preserving persistent web configuration overrides.

## Compile-time defaults

Edit `include/compile_defaults.h` inside the board project before compiling. Supported values are Wi-Fi SSID/password, Ambient application/API keys, optional station MAC, hostname, POSIX timezone, poll interval, and stale threshold.

The checked-in files intentionally contain blank credentials.

## Persistence model

On completely blank NVS, the compiled defaults seed the active configuration once and are immediately stored in Preferences/NVS. On subsequent boots, the stored NVS values are authoritative. Changes saved from `/config` persist across reboots and are not overwritten by the compiled defaults.

Existing pre-V7.4 NVS keys are treated as a legacy configuration and preserved. Factory Reset clears NVS; the compiled defaults seed again on the next boot.

## Current driver pins

- T-Display-S3 uses the native LovyanGFX Parallel8 profile and pins `LovyanGFX@1.2.7`.
- Waveshare 2.8-inch pins `GFX Library for Arduino@1.6.0`.

## Build

From either board directory:

```bash
pio run -t clean
pio run
pio run -t upload
```

On Windows, `CLEAN_BUILD_WINDOWS.bat` removes the entire `.pio` dependency cache before building.
