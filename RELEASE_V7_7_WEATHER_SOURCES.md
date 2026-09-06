# Production Release V7.7 — selectable weather sources

V7.7 adds a persistent web-configurable weather source for both production
boards. Existing installations migrate to **Ambient Weather** automatically,
so saved Ambient credentials and station selection continue to work unchanged.

Supported providers:

- **Ambient Weather** — existing `rt.ambientweather.net` current and history APIs.
- **Weather Underground** — PWS current observations from
  `api.weather.com/v2/pws/observations/current` and historical observations from
  `api.weather.com/v2/pws/history/all`.

Weather Underground configuration requires a PWS Station ID and API key. The
firmware requests imperial units with decimal precision and continues to run
the same local NWS heat-index/wind-chill calculations used for Ambient data.
Historical PWS records use `tempHigh`, `tempLow`, `tempAvg`, and `windgustHigh`
to calculate Today's High/Low, maximum daily gust, and the observation nearest
the same time yesterday.

The selected provider, credentials, and station identifier are persisted in
Preferences/NVS. `compile_defaults.h` now supports first-boot defaults for the
source and both providers. Provider changes made in the web UI remain the source
of truth until Factory Reset.
