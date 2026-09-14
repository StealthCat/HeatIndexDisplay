from pathlib import Path

path = Path("Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp")
text = path.read_text()

old = '''static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {
  setText(color, size);
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
  gfx->setCursor(x, y + 1);
  gfx->print(text);
}

static void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  int x = centerX - (int)w / 2;
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
  gfx->setCursor(x, y + 1);
  gfx->print(text);
}
'''

new = '''// The Arduino_GFX built-in bitmap font is already aligned to the physical
// pixel grid.  Repainting each glyph at +1 X/Y to fake bold text caused
// visible smearing and stair-stepped edges on the 240x320 Waveshare panel.
// Keep these helpers for the existing layout API, but render every glyph once
// so labels, values, the header, risk pill and footer stay crisp.
static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {
  setText(color, size);
  gfx->setCursor(x, y);
  gfx->print(text);
}

static void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  int x = centerX - (int)w / 2;
  gfx->setCursor(x, y);
  gfx->print(text);
}
'''

if old not in text:
    raise SystemExit("Expected synthetic-bold helper block was not found; refusing to patch")

text = text.replace(old, new, 1)
path.write_text(text)

# Contract checks: no synthetic +1 overdraw should remain in the two helpers.
patched = path.read_text()
start = patched.index("static void printBoldAt")
end = patched.index("static void drawConceptCard", start)
helper_block = patched[start:end]
assert "setCursor(x + 1" not in helper_block
assert "setCursor(x, y + 1" not in helper_block
assert helper_block.count("gfx->print(text);") == 2
print("Waveshare 2.8 text rendering changed to single-pass pixel-aligned glyphs")
