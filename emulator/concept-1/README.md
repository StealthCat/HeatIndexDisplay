# Concept-1 emulator

Browser emulator for the production **Concept-1 Waveshare ESP32-S3-Touch-LCD-7C-BOX** display.

## Run

Open `index.html` directly, or serve this directory with any static HTTP server. The emulated panel is exactly 800×480 pixels and controls below it let you exercise heat, cold, wind, forecast, yesterday-delta, and stale-data states.

## Sync contract

`sync-manifest.json` pins the production `display_ui.cpp` and `weather_math.cpp` Git blob SHAs. `verify-sync.mjs` fails if those production sources drift without a corresponding emulator update, and also checks the emulator's core layout, formulas, thresholds, palettes, forecast rotation, and footer state.

Run from the repository root:

```bash
node emulator/concept-1/verify-sync.mjs
```

When production Concept-1 UI or apparent-temperature math changes, update the emulator first, then update the pinned source SHA(s) in the manifest. CI will otherwise fail intentionally.
