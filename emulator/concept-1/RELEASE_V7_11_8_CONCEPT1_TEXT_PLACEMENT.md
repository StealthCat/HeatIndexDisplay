# Emulator V7.11.8 Concept 1 — text placement correction

Emulator-only. Production firmware is unchanged.

The Concept 1 hero panels now position the apparent-temperature number,
degree symbol and Fahrenheit marker independently. This prevents 3-digit
values such as 100°F from colliding with the large sun icon or clipping the
unit at the edge of either display.

Additional adjustments:
- Waveshare sun moved up/left and reduced slightly
- Waveshare apparent temperature moved lower/right to match Concept 1
- LILYGO sun reduced slightly so 100°F remains fully visible
- Hero titles rebalanced
- Waveshare GUST/MAX lines spaced for clearer rendering
