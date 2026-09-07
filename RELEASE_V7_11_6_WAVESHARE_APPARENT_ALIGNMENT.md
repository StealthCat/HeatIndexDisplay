# V7.11.6 — Waveshare apparent-temperature alignment

This production fix corrects apparent-temperature alignment on the Waveshare ESP32-S3 Touch LCD 2.8.

The previous layout centered only the numeric digits and then appended the degree marker and `F`. With a three-digit heat index such as `100`, that pushed the unit pair too far right.

V7.11.6 measures the numeric value and Fahrenheit glyph, calculates the width of the complete value + degree + F group, and centers that complete group inside the 128-pixel apparent-temperature panel. The degree marker is also given an explicit superscript position relative to the number.

No weather calculations, provider APIs, polling behavior, forecast behavior, or LILYGO layout are changed.
