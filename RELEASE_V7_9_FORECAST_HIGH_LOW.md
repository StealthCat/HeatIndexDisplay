# Production V7.9 - Forecast High / Low

V7.9 changes the display High / Low card from observed daily extrema to forecast temperatures.

- Ambient Weather and Weather Underground continue to supply current observations.
- From Yesterday continues to come from the configured provider history REST API.
- The current provider payload supplies station latitude/longitude.
- Forecast High / Low uses Open-Meteo `temperature_2m_max` and `temperature_2m_min` in Fahrenheit with `timezone=auto` and a two-day forecast window.
- The card displays Today for 30 seconds, then Tomorrow for 30 seconds, repeating continuously.
- Forecast data refreshes every 15 minutes, with a 60-second retry until the first success.
- Forecast failures do not interfere with current observations or From Yesterday.

Open-Meteo is the common forecast source because Ambient Weather's documented REST API exposes past/present station data rather than forecast data, while Weather Company forecast products may require separate forecast entitlements beyond a PWS observation key.
