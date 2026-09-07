# V7.11.5 — Production display refinement

This release promotes the emulator-approved V7.11.2–V7.11.5 display refinements to both production firmware targets.

## LILYGO T-Display S3

- Small metric cards use a consistent Dew-Point-style label/value rhythm.
- Non-forecast values are nudged upward for better optical alignment.
- Metric icons are vertically centered within their cards.
- The footer now shows `Updated <time>` at left and `ONLINE` / `STALE` at right.
- Forecast card behavior and its 30-second Today/Tomorrow switching are unchanged.

## Waveshare ESP32-S3 Touch LCD 2.8

- The main apparent-temperature card is taller.
- All four upper metric cards are taller and reflowed into the reclaimed space.
- Wind, Direction, and Forecast cards are reduced to a shorter 48-pixel row.
- Wind and direction icons are centered vertically in the shorter cards.
- The direction bearing is lowered to visually align with the compass icon.
- Forecast high/low values remain at the largest classic-font scale that fits both degree-marked values in the card.
- All existing provider, historical REST, forecast, stale-state, and polling behavior is unchanged.
