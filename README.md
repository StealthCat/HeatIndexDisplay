# WS-5000 AmbientWeather.net Heat Index Firmware (Mockup-Matched)

These are updated cloud/API firmware projects for:

- T-Display-S3
- Waveshare-ESP32-S3-Touch-LCD-2.8

This revision changes the live display layout so it visually follows the final
mockup: no logo, no slogan, dark UI, bold red/orange heat-index panel, station
name at the top, and a cleaner footer.


## Wind chill update

This revision automatically displays **WIND CHILL** instead of **HEAT INDEX** whenever NWS wind-chill conditions apply (temperature at or below 50 F and wind above 3 mph). It also exposes `wind_chill_f`, `apparent_f`, and `mode` in the JSON status output.


## Production maintenance update — 2026-09-05

This release includes the compiler fixes discovered during Wokwi validation.
See `PRODUCTION_UPDATE.md` for details. Emulator-specific software-SPI changes
are deliberately not used on the physical boards.


## Performance-optimized production release

This release avoids unnecessary footer/full-screen redraws and uses a 20 ms
idle loop delay. See `PERFORMANCE_UPDATE.md`.


## Production Performance V2

This package adds the standard-C++ forward declarations required by the
performance helpers. See `V2_COMPILE_FIX.md`.


## Mockup Match V3

The physical UI now implements the approved heat-index and wind-chill mockup layouts. See `MOCKUP_MATCH_V3.md`.


## Mockup Match V4

Standalone header clocks are removed. Observation/update timestamps remain in the footer.


## Mockup Match V5

Waveshare lower-card alignment has been corrected. See `MOCKUP_MATCH_V5.md`.


## Mockup Match V6

The T-Display normal weather header contains no standalone current-time clock. The footer observation timestamp remains.


## Production Release V7

This package contains the final approved production layout, including the finalized Waveshare lower-card alignment. See `RELEASE_V7.md`.


## V7.1 Arduino_GFX fix

The Waveshare build now pins `GFX Library for Arduino@1.6.0`. Delete the entire `.pio` directory before the first V7.1 build. See `V7_1_GFX_FIX.md` in the combined release.


## Production Release V7.2

Adds missing standard-C++ forward declarations required by PlatformIO. See `RELEASE_V7_2.md`.


## Production Release V7.3

The T-Display-S3 now uses a direct LovyanGFX hardware profile and no longer depends on LilyGo-display-library. Remove `.pio` before the first build.


## Production Release V7.4

Both boards now support optional compile-time first-boot Wi-Fi and AmbientWeather.net defaults while preserving persistent web-configuration overrides. See `RELEASE_V7_4.md`.
