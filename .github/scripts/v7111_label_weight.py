from pathlib import Path


def rep(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise RuntimeError(f'pattern not found: {path}')
    p.write_text(s.replace(old, new, 1))

# Add a subtle one-pixel vertical weight pass. This makes the compact-card text
# visibly larger/heavier without forcing a font jump that would no longer fit.
t = 'T-Display-S3/src/display_ui.cpp'
rep(t,
'''static void drawBoldText(const String &text, int x, int y, uint16_t color) {
  display.setTextColor(color);
  display.drawString(text, x, y);
  display.drawString(text, x + 1, y);
}''',
'''static void drawBoldText(const String &text, int x, int y, uint16_t color) {
  display.setTextColor(color);
  display.drawString(text, x, y);
  display.drawString(text, x + 1, y);
  display.drawString(text, x, y + 1);
}''')

w = 'Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp'
rep(w,
'''static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {
  setText(color, size);
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
}''',
'''static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {
  setText(color, size);
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
  gfx->setCursor(x, y + 1);
  gfx->print(text);
}''')

rep(w,
'''static void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  int x = centerX - (int)w / 2;
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
}''',
'''static void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {
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
}''')
