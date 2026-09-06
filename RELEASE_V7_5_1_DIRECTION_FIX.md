# Production Release V7.5.1 — Waveshare direction helper compile fix

V7.5.1 fixes the Waveshare compile error:

    'directionLongText' was not declared in this scope

## Cause

During V7.5, the primitive icon-rendering block was replaced with the new RGB565 asset-based icon renderer. The existing `directionLongText()` helper was inside the replaced source range and was unintentionally removed, while its call in `drawWeatherScreen()` remained.

## Fix

The Waveshare source once again contains the long-form compass-direction helper and now also includes an explicit forward declaration near the top of `main.cpp`.

No display layout, icon asset, weather calculation, network behavior, or configuration behavior changed from V7.5.
