# Concept-1 emulator

Browser emulator for the production **Concept-1 Waveshare ESP32-S3-Touch-LCD-7C-BOX** firmware.

## Run

```bash
cd emulator/concept-1
python3 server.py
```

Open `http://127.0.0.1:8080`.

The emulator has two data modes:

- **Preset/Test Data** — editable values and risk presets.
- **Live Weather Data** — polls either Ambient Weather or Weather Underground through the local Python server. Provider credentials are kept in memory only and are never written to disk.

Live mode mirrors the production Concept-1 data flow: current station observations, provider REST history for today's high/low and the same local clock time yesterday, Weather Underground recent/hourly → daily → archived fallback order, provider station coordinates, and a two-day Open-Meteo high/low forecast. Current observations continue updating when a secondary history/forecast request fails; the last valid secondary values remain displayed.

## Sync verification

`sync-manifest.json` pins the production UI, math, provider, forecast, and endpoint/config source blobs. CI runs:

```bash
node emulator/concept-1/verify-sync.mjs
```

The check fails if a pinned production source changes without a corresponding emulator update, or if required emulator formulas, geometry, provider fallbacks, modes, or forecast behavior disappear.
