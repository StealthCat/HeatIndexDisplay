# Emulator V7.8 — Provider REST Summary Parity

This release copies the production V7.8 summary-data behavior into the desktop emulator.

## Ambient Weather

- Current weather remains sourced from `/v1/devices`.
- Today High/Low use `/v1/devices/{MAC}` with explicit `endDate` and `limit=288`.
- From Yesterday uses a second request ending at the same local wall-clock time yesterday with `limit=2`.

## Weather Underground

- Current weather remains sourced from `/v2/pws/observations/current`.
- Today High/Low prefer `/v2/pws/history/daily`.
- `/v2/pws/history/all` is used as the current-day fallback and for yesterday's same-time observation.

## Reliability

- Yesterday is calculated by local calendar day, not a hard-coded 24-hour subtraction, so DST transitions keep the comparison at the same wall-clock time.
- Current observations and successfully refreshed Today High/Low remain visible even if the independent yesterday-history request fails.
- Preset/Test Data versus Live Weather Data behavior from V7.7.1 is retained unchanged.
