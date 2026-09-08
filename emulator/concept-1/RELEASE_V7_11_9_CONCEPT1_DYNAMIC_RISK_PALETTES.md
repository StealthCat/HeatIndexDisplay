# Emulator V7.11.9 Concept 1 — dynamic risk palettes

Ports all current Concept 1 production palette changes to the emulator.

Heat Index hero colors now follow the same production progression:
- <80°F: green
- 80–89°F: yellow/gold
- 90–102°F: orange
- 103–124°F: red
- >=125°F: magenta/purple

Wind Chill hero colors now follow the same NWS-guided production progression:
- >-18°F: deep blue
- -18°F to -31°F: icy/light blue
- -32°F to -47°F: deeper blue
- <=-48°F: purple

For both modes the hero gradient, border, risk pill, and risk accent change
together while retaining the Concept 1 visual style.

No production firmware is modified by this emulator package.
