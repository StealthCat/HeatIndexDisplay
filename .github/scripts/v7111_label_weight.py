from pathlib import Path


def rep(path, old, new):
    p=Path(path); s=p.read_text()
    if old not in s: raise RuntimeError(f'pattern not found: {path}')
    p.write_text(s.replace(old,new))

# Add a subtle one-pixel vertical weight pass. This makes the compact-card text
# visibly larger/heavier without forcing a font jump that would no longer fit.
t='T-Display-S3/src/display_ui.cpp'
rep(t,
'''static void drawBoldText(const String &text, int x, int y, uint16_t color) {\n  display.setTextColor(color);\n  display.drawString(text, x, y);\n  display.drawString(text, x + 1, y);\n}''',
'''static void drawBoldText(const String &text, int x, int y, uint16_t color) {\n  display.setTextColor(color);\n  display.drawString(text, x, y);\n  display.drawString(text, x + 1, y);\n  display.drawString(text, x, y + 1);\n}''')

w='Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp'
rep(w,
'''  gfx->setCursor(x + 1, y);\n  gfx->print(text);\n}''',
'''  gfx->setCursor(x + 1, y);\n  gfx->print(text);\n  gfx->setCursor(x, y + 1);\n  gfx->print(text);\n}''')
rep(w,
'''  gfx->setCursor(x + 1, y);\n  gfx->print(text);\n}\n\nvoid drawSunIcon''',
'''  gfx->setCursor(x + 1, y);\n  gfx->print(text);\n  gfx->setCursor(x, y + 1);\n  gfx->print(text);\n}\n\nvoid drawSunIcon''')
