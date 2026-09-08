# Emulator V7.9 — Forecast High/Low parity

This emulator release mirrors production V7.9.

- Adds station latitude/longitude to emulator weather state.
- Extracts coordinates from Ambient Weather and Weather Underground current observations.
- Adds Open-Meteo two-day forecast retrieval using the same production query.
- Refreshes successful forecasts every 15 minutes and retries initial failures every 60 seconds.
- Changes both emulated display High/Low cards to forecast values.
- Alternates Today's and Tomorrow's forecast High/Low every 30 seconds.
- Keeps From Yesterday and observed historical summaries sourced from the configured provider REST API.
- Adds forecast values, current forecast-card phase, coordinates, and forecast errors to the browser status view.
