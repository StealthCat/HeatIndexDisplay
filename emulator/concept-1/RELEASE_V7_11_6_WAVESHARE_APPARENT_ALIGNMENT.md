# Emulator V7.11.6 — Waveshare apparent-temperature alignment

This emulator update mirrors the V7.11.6 production fix.

The Waveshare apparent-temperature display now centers the complete temperature
group — numeric value, degree marker, and Fahrenheit indicator — rather than
centering only the numeric digits.

This specifically prevents three-digit values such as `100°F` from shifting the
degree/F portion too far toward the right edge. Two-digit and three-digit values
now use the same centered group behavior.

No provider, polling, forecast, historical API, calculation, LILYGO layout, or
other Waveshare geometry was changed.
