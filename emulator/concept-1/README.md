# HeatIndexDisplay Emulator — V7.11.9 Concept 1

Desktop/browser emulator for the current production HeatIndexDisplay firmware.

## Production parity

The V7.11.9 Concept 1 emulator mirrors the production behavior for both supported displays:

- **LILYGO T-Display S3** — 170×320 portrait
- **Waveshare ESP32-S3 Touch LCD 2.8** — 240×320 portrait
- automatic Heat Index / Wind Chill switching
- the same NWS Heat Index and Wind Chill equations and risk labels
- Ambient Weather / Weather Underground source selection
- provider REST history for **From Yesterday** and observed summary values
- station latitude/longitude extraction from the configured provider
- **Open-Meteo forecast High/Low** for today and tomorrow
- the High/Low card alternates **Today's** and **Tomorrow's** forecast every **30 seconds**
- forecast refresh every **15 minutes** after a successful forecast
- **60-second retry** until the first successful forecast
- Preset / Test Data and Live Weather Data modes
- stale-data, provider-error, summary-error, and forecast-error status

The display High/Low card is forecast data in V7.11.9 Concept 1. The provider-history `today_high_f` / `today_low_f` values are retained for diagnostics and API parity but are no longer what the display card renders.

## Requirements

Python 3.10+ only. No third-party packages are required.

## Run on Windows

Double-click:

    run_emulator.bat

or:

    py main.py

Then browse to:

    http://127.0.0.1:8765/

## Run on Linux / macOS

    ./run_emulator.sh

or:

    python3 main.py

## Data modes

**Preset / Test Data** never contacts Ambient Weather, Weather Underground, or Open-Meteo. Presets include mock today/tomorrow forecasts so the 30-second card alternation can be tested immediately.

**Live Weather Data** polls the selected provider for station observations and history, extracts the station coordinates, then uses those coordinates to retrieve the two-day forecast from Open-Meteo.

## Live provider behavior

### Ambient Weather

Current conditions and coordinates come from `/v1/devices`. History comes from `/v1/devices/{MAC}`. The emulator preserves the production V7.8.1/V7.11.9 Concept 1 logic for Today observed High/Low and the same-local-time-yesterday comparison.

### Weather Underground

Current conditions and coordinates come from `/v2/pws/observations/current`. Provider history prefers recent 7-day hourly observations, then recent 1-day data, then archived daily/all history as fallbacks.

### Forecast

The current production firmware uses:

    https://api.open-meteo.com/v1/forecast

with:

    daily=temperature_2m_max,temperature_2m_min
    temperature_unit=fahrenheit
    timezone=auto
    forecast_days=2

The emulator uses the same query and refresh cadence.

## Manual testing

The preset buttons exercise Heat Index, Wind Chill, Normal, Stale, and Waiting states. Manual values can be entered for current weather, provider-history values, and today/tomorrow forecast High/Low.

## Status panel

The browser status output includes:

- selected weather provider
- provider REST summary source
- observed Today High/Low
- Yesterday temperature / From Yesterday
- station latitude/longitude
- Open-Meteo forecast today and tomorrow High/Low
- which forecast card is currently visible
- seconds until the next 30-second card switch
- forecast HTTP/error status

## Tests

Run:

    py -m unittest discover -s tests -v

The V7.11.9 Concept 1 suite covers weather math, provider history behavior, provider coordinate extraction, Open-Meteo forecast parsing, 30-second Today/Tomorrow switching, both display renderers, and live controller forecast integration.

## Architecture

The emulator follows the modular production structure:

- `app_state.py`
- `weather_math.py`
- `config_store.py`
- `weather_source.py`
- `ambient_weather.py`
- `wunderground_weather.py`
- `forecast_weather.py`
- `display_ui.py`
- `web_ui.py`
- `app_controller.py`

ESP32 GPIO, SPI/Parallel8, NVS, AP-mode Wi-Fi, LovyanGFX, and Arduino_GFX are replaced by desktop equivalents.

## V7.11.9 Concept 1 display polish

The emulator renderer now mirrors the production V7.11.9 Concept 1 visual hierarchy. Small blue cards show their label first and the associated value beneath it, with stronger/bolder typography, brighter borders, and clearer WIND, DIRECTION, and forecast cards.

The underlying V7.9 provider, historical REST, forecast, and 30-second Today/Tomorrow behavior is unchanged.

## V7.11.9 Concept 1 display parity

The emulator now matches the latest production display spacing, weight,
degree-symbol formatting, wind alignment, and enlarged forecast values.

## V7.11.9 Concept 1 emulator-only refinement

This version previews additional layout refinements without changing production
firmware. LILYGO metric cards now follow the Dew Point card's spacing/type
treatment; Waveshare direction, forecast, wind icon, and mph positioning are
rebalanced.

## V7.11.9 Concept 1 emulator-only icon alignment

All metric and forecast icons are vertically centered in their cards. On the
Waveshare preview, the large forecast temperature line is also shifted upward
and right for better use of the forecast-card space. Production firmware remains
unchanged.

## V7.11.9 Concept 1 emulator-only layout rebalance

LILYGO values are nudged upward and its footer now includes ONLINE/STALE.
Waveshare gives more vertical space to the upper cards while shortening and
reflowing the bottom Wind, Direction, and Forecast cards.

## V7.11.9 Concept 1 emulator-only Waveshare refinement

The Waveshare preview now gives substantially more vertical space to the main
and upper metric cards while shrinking the Wind/Direction/Forecast row. The
direction bearing is lowered to line up with its compass, and the forecast
temperature line is larger. Production firmware remains unchanged.

## V7.11.9 Concept 1 Waveshare apparent-temperature alignment

The Waveshare emulator now centers the complete apparent-temperature group
(value + degree mark + F), matching the V7.11.9 Concept 1 production fix for three-digit
heat-index values.

## V7.11.9 Concept 1 visual reimagine

The emulator now matches the first approved reimagined display concept: black
screens, amber Heat Index hero cards, deep navy metric cards, cyan outlines,
large condition icons, outlined risk pills, and clock/status footers. All
existing data and behavior remain available. Production firmware is unchanged.

## V7.11.9 Concept 1 text-placement correction

The Concept 1 hero temperature now uses explicit number/degree/F positioning,
so 3-digit apparent temperatures remain fully visible and do not overlap the
large condition icon. Production firmware remains unchanged.

## V7.11.9 Concept 1 dynamic risk palettes

The emulator now mirrors all current `concept-1` production palette behavior:
dynamic Heat Index green/yellow/orange/red/magenta gradients and dynamic Wind
Chill blue/icy-blue/deep-blue/purple gradients, including matching hero borders
and risk pills.
