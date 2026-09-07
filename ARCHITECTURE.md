# Firmware architecture

Both production targets use the same functional module boundaries. The only
board-specific implementation is `src/display_ui.cpp`.

| Module | Responsibility |
| --- | --- |
| `main.cpp` | Arduino entry points only |
| `app_state.*` | Shared configuration/weather/runtime state |
| `app_controller.*` | Startup and main-loop orchestration |
| `config_store.*` | Preferences/NVS persistence and compile-default migration |
| `weather_math.*` | Heat index, wind chill, dew point, risk labels and wind direction |
| `weather_source.*` | Selects the configured provider and dispatches polling |
| `ambient_weather.*` | AmbientWeather REST polling, JSON parsing, history summary and rate limiting |
| `wunderground_weather.*` | Weather Underground PWS current/history polling and JSON parsing |
| `forecast_weather.*` | Two-day forecast high/low retrieval and 30-second Today/Tomorrow card phase |
| `time_utils.*` | Observation age, stale detection and date/time formatting |
| `wifi_manager.*` | Wi-Fi STA/AP connection and setup-AP behavior |
| `web_ui.*` | Configuration/status HTTP routes and HTML UI |
| `ui_state.*` | Redraw/change detection and footer state key |
| `display_ui.*` | Board-specific display driver, icons and approved production layout |
| `ui_assets.h` | Fixed RGB565 icon assets |

The refactor intentionally preserves the existing behavior and approved V7.5
screen geometry. It replaces the single large translation unit with normal C++
headers and source files; no `.inc` fragments are used.
