# Emulator V7.7.1 — Live Data Mode Fix

This emulator update adds an explicit **Data Mode** selector and fixes live-provider refresh behavior.

## Data modes

- **Preset / Test Data** — uses only preset or manually entered weather values and never polls a provider.
- **Live Weather Data** — automatically polls the selected Ambient Weather or Weather Underground provider at `poll_seconds`.

## Live update fix

Current weather is now committed to the emulator display before historical summary data is considered complete. If the provider current-observation request succeeds but its history/summary request fails, the display still updates with the current observation and retains the previous successful summary values. This matches the production firmware behavior more closely.

Switching from preset mode to live mode clears mock values immediately, so stale preset data cannot be mistaken for live weather.
