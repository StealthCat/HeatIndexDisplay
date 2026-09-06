# Production Release V7.6 — modular source refactor

V7.6 restructures both production projects into normal C++ modules grouped by
functional responsibility. The refactor is intended to be behavior-preserving:
weather calculations, AmbientWeather API behavior, persistent configuration,
Wi-Fi/setup AP behavior, icon assets, and approved display geometry remain the
same as V7.5.1.

The previous monolithic `src/main.cpp` is now a small Arduino entry point.
Functional code is separated into `app_state`, `app_controller`,
`config_store`, `weather_math`, `ambient_weather`, `time_utils`,
`wifi_manager`, `web_ui`, `ui_state`, and board-specific `display_ui` modules.

This structure also prevents display helpers such as wind-direction formatting
from being accidentally removed when icon/rendering code changes.
