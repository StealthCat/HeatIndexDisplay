# HeatIndexDisplay — Concept 1

ESP32-S3 apparent-temperature displays for personal weather-station data from **Ambient Weather** or **Weather Underground**, including the 800×480 Waveshare 7C-BOX Concept-1 dashboard and its desktop/browser emulator.

This README is the **single documentation source for the `concept-1` branch and emulator**. Historical release-note and nested README files have been consolidated here.

## Branches

- **`main`** — stable production firmware for the LILYGO T-Display S3 and Waveshare 2.8-inch display.
- **`concept-1`** — adds the Waveshare ESP32-S3 Touch LCD 7C-BOX and the Concept-1 emulator while retaining the production weather-source, history, forecast, and apparent-temperature behavior.

## Supported hardware

| Target | Resolution | Display / driver |
| --- | ---: | --- |
| LILYGO T-Display S3 | 170×320 | ST7789, LovyanGFX Parallel8 |
| Waveshare ESP32-S3 Touch LCD 2.8 | 240×320 | ST7789 SPI |
| Waveshare ESP32-S3 Touch LCD 7C-BOX | 800×480 | ST7262 RGB565 |

The 7C-BOX build uses the Concept-1 landscape information hierarchy: station/date header, Current Conditions subtitle, apparent-temperature hero, four metric cards, Wind/Direction/Forecast row, and Updated/ONLINE footer. Touch input is not required by the weather dashboard.

## Display behavior

The firmware automatically switches between **Heat Index** and **Wind Chill** based on current conditions. The dashboard includes:

- apparent temperature and risk status
- air temperature
- humidity
- dew point
- From Yesterday comparison
- wind speed and gust
- maximum daily gust
- 16-point wind direction
- Today / Tomorrow forecast high and low
- updated time and ONLINE / STALE state

### Concept-1 palettes

The 7C-BOX Concept-1 presentation uses dynamic risk palettes rather than a single fixed hero treatment.

Heat Index transitions through green, yellow, orange, red, and magenta risk treatments as apparent temperature increases. Wind Chill transitions through blue, icy blue, deep blue, and purple treatments as cold risk increases. Hero gradients, borders, and risk pills move together so risk state remains visually consistent.

The apparent-temperature group is centered as a complete **value + degree + F** unit so three-digit Heat Index values remain correctly aligned.

## Weather calculations

Heat Index uses the NWS simple estimate and Rothfusz regression with standard humidity adjustments. Wind Chill is used when temperature is 50°F or below and wind speed exceeds 3 mph. Dew point uses the Magnus approximation. Wind direction is rendered on a 16-point compass.

## Weather sources and history

The provider is selectable from the configuration interface.

### Ambient Weather

Current conditions and coordinates come from the Ambient Weather device API. REST history provides observed summary data and the same-local-time-yesterday comparison. Yesterday matching is timezone-aware so DST transitions do not shift the intended local comparison time.

### Weather Underground

Current conditions and coordinates come from the Weather Underground PWS current-observation endpoint. Historical data prefers recent seven-day hourly observations, then recent one-day observations, then daily/archived history fallbacks.

Secondary history failures do not discard the most recent valid summary values.

## Forecast

Station coordinates from the configured provider are used with Open-Meteo's two-day daily forecast API. The forecast card alternates:

- **Today** for 30 seconds
- **Tomorrow** for 30 seconds

Forecast data refreshes every 15 minutes after a successful fetch, with shorter retries until the first successful forecast. The display High/Low card is forecast data; provider-history high/low values remain available for diagnostics and API parity.

## Firmware configuration

With no stored Wi-Fi configuration, the device starts a `HeatIndex-Setup-XXXX` access point. Connect and open:

```text
http://192.168.4.1/config
```

The configuration panel controls Wi-Fi, hostname, timezone, weather provider, provider credentials/station identifiers, polling interval, and stale-data threshold. Stored secrets are not rendered back into the page.

### Compile-time defaults

Each hardware project includes `include/compile_defaults.h`. Compiled values seed NVS only when NVS is blank. Saved web configuration persists and overrides compile-time defaults. Factory Reset clears NVS and permits defaults to seed again.

**Do not commit real Wi-Fi passwords or weather API keys to this public repository.**

## Build firmware

Each target is an independent PlatformIO project.

```bash
cd T-Display-S3
pio run
```

```bash
cd Waveshare-ESP32-S3-Touch-LCD-2.8
pio run
```

```bash
cd Waveshare-ESP32-S3-Touch-LCD-7C-BOX
pio run
```

For a clean Windows firmware build, use the `CLEAN_BUILD_WINDOWS.bat` file in the selected hardware directory.

## Firmware architecture

The firmware is modular by functional area:

- `app_controller` — application lifecycle and polling orchestration
- `app_state` — shared weather/configuration state
- `config_store` — NVS-backed configuration
- `wifi_manager` — Wi-Fi and setup access-point behavior
- `weather_source` — provider selection
- `ambient_weather` — Ambient Weather current/history client
- `wunderground_weather` — Weather Underground current/history client
- `forecast_weather` — Open-Meteo forecast client
- `weather_math` — apparent temperature, dew point, risk, and compass calculations
- `display_ui`, `ui_state`, `ui_assets` — dashboard presentation
- `web_ui` — configuration/status interface

`src/main.cpp` intentionally remains small and delegates to these components.

# Concept-1 Emulator

The emulator lives in:

```text
emulator/concept-1/
```

It is the V7.11.9 Concept-1 desktop/browser implementation and mirrors the production data flow while replacing ESP32 hardware, GPIO, display buses, NVS, and embedded web plumbing with desktop equivalents.

## Emulator requirements

- Python 3.10+
- no third-party Python packages required

## Run the emulator

### Windows

```text
emulator\concept-1\run_emulator.bat
```

or:

```bash
cd emulator/concept-1
py main.py
```

### Linux / macOS

```bash
cd emulator/concept-1
./run_emulator.sh
```

or:

```bash
python3 main.py
```

Then open:

```text
http://127.0.0.1:8765/
```

## Emulator data modes

### Preset / Test Data

Never contacts Ambient Weather, Weather Underground, or Open-Meteo. Presets and manual fields exercise Heat Index, Wind Chill, risk palettes, stale/waiting states, provider-history values, and Today/Tomorrow forecast switching.

### Live Weather Data

Polls the selected provider for current observations and REST history, extracts station coordinates, and retrieves the two-day forecast from Open-Meteo using the same provider/forecast semantics as firmware.

The browser status view reports provider state, summary source, observed daily values, Yesterday / From Yesterday, station coordinates, forecast values, current forecast card, switch countdown, and provider/forecast errors.

## Emulator architecture

The Python package mirrors the firmware's modular organization:

- `emulator/app_state.py`
- `emulator/weather_math.py`
- `emulator/config_store.py`
- `emulator/weather_source.py`
- `emulator/ambient_weather.py`
- `emulator/wunderground_weather.py`
- `emulator/forecast_weather.py`
- `emulator/display_ui.py`
- `emulator/web_ui.py`
- `emulator/app_controller.py`

Supporting files include `main.py`, `config.example.json`, launch scripts, SVG previews, and the unit-test suite.

## Emulator tests

From `emulator/concept-1` run:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers weather math, provider REST history behavior, provider coordinate extraction, Open-Meteo parsing, 30-second Today/Tomorrow switching, Concept-1 display rendering, dynamic risk palettes, and controller integration.

## Emulator source parity

The downloadable source archive remains **HeatIndexDisplay-Emulator-V7.11.9-Concept1.zip** with source SHA-256:

```text
2c74b84b08e240e6c1c30f4b8410ca6a9a955cb416b8cfbca77d180d95379059
```

The repository intentionally omits the archive's embedded Markdown documentation because all documentation is consolidated into this root `README.md`. CI verifies the remaining **30 functional emulator files** against their hashes from the downloadable package and runs the full test suite.

## Consolidated release history

### Production firmware

- **V7.4** — compile-time defaults for production targets.
- **V7.5** — RGB565 icon assets for closer mockup matching.
- **V7.5.1** — Waveshare direction-helper restoration.
- **V7.6** — modular firmware refactor.
- **V7.7** — selectable Ambient Weather / Weather Underground source.
- **V7.8** — provider REST history for observed Today High/Low and From Yesterday.
- **V7.8.1** — provider-local history and Weather Underground fallback improvements.
- **V7.9** — Open-Meteo Today/Tomorrow forecast High/Low and 30-second alternation.
- **V7.10** — display hierarchy and typography polish.
- **V7.11.5** — production display refinements and ONLINE/STALE footer improvements.
- **V7.11.6** — Waveshare apparent-temperature value/degree/F alignment.
- **Concept 1** — 800×480 Waveshare 7C-BOX implementation and cold-risk palette refinement.

### Emulator / Concept-1 progression

- **V7.7.1** — live-mode fixes.
- **V7.8 / V7.8.1** — provider REST summary and live-summary fixes.
- **V7.9** — forecast High/Low parity.
- **V7.10** — display polish.
- **V7.11.1** — display refinement.
- **V7.11.2** — emulator layout refinement.
- **V7.11.3** — icon alignment.
- **V7.11.4** — layout rebalance.
- **V7.11.5** — Waveshare emulator rebalance.
- **V7.11.6** — apparent-temperature alignment.
- **V7.11.7** — Concept-1 visual reimagine.
- **V7.11.8** — Concept-1 text-placement correction.
- **V7.11.9** — dynamic Heat Index and Wind Chill risk palettes matching current Concept-1 behavior.

## Documentation policy

This branch intentionally keeps **one Markdown documentation file: this root `README.md`**. New setup notes, architecture changes, release summaries, and emulator documentation should be added here rather than creating additional README or release-note Markdown files.
