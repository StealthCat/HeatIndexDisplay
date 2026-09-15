from pathlib import Path

path = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
s = path.read_text()

include_needle = '#include "ui_assets.h"\n\n#include <Arduino_GFX_Library.h>\n'
include_repl = '''#include "ui_assets.h"\n\n#include <Arduino_GFX_Library.h>\n#include "fonts/FreeSans8pt7b.h"\n#include "fonts/FreeSans10pt7b.h"\n#include "fonts/FreeSans16pt7b.h"\n#include "fonts/FreeSans18pt7b.h"\n'''
assert include_needle in s, 'include insertion point not found'
s = s.replace(include_needle, include_repl, 1)

old_text_helpers = '''void setText(uint16_t color, uint8_t size) {\n  gfx->setTextColor(color);\n  gfx->setTextSize(size);\n}\n\nvoid centerText(const String &text, int centerX, int baselineY, uint8_t size, uint16_t color) {\n  setText(color, size);\n  int16_t x1, y1;\n  uint16_t w, h;\n  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);\n  gfx->setCursor(centerX - (int)w / 2, baselineY);\n  gfx->print(text);\n}\n'''
new_text_helpers = '''static const GFXfont *uiFontForSize(uint8_t size) {\n  // Use native rasterized FreeSans sizes instead of enlarging the 5x7 bitmap\n  // font. This keeps curves/diagonals smooth and also reduces the visual size.\n  if (size <= 1) return &FreeSans8pt7b;\n  if (size == 2) return &FreeSans10pt7b;\n  if (size <= 4) return &FreeSans16pt7b;\n  return &FreeSans18pt7b;\n}\n\nvoid setText(uint16_t color, uint8_t size) {\n  gfx->setFont(uiFontForSize(size));\n  gfx->setTextColor(color);\n  gfx->setTextSize(1);\n}\n\nstatic void setCursorForTopLeft(const String &text, int x, int y) {\n  int16_t x1, y1;\n  uint16_t w, h;\n  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);\n  gfx->setCursor(x - x1, y - y1);\n}\n\nvoid centerText(const String &text, int centerX, int topY, uint8_t size, uint16_t color) {\n  setText(color, size);\n  int16_t x1, y1;\n  uint16_t w, h;\n  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);\n  gfx->setCursor(centerX - (int)w / 2 - x1, topY - y1);\n  gfx->print(text);\n}\n'''
assert old_text_helpers in s, 'base text helper block not found'
s = s.replace(old_text_helpers, new_text_helpers, 1)

start = s.index('// The Arduino_GFX built-in bitmap font is already aligned')
end = s.index('\nstatic void drawConceptCard', start)
new_render_helpers = '''// FreeSans is rendered at the target size, so no synthetic bold overdraw or\n// integer bitmap scaling is needed. Coordinates remain top-left based to keep\n// the existing layout stable while changing font technology.\nstatic void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {\n  setText(color, size);\n  setCursorForTopLeft(text, x, y);\n  gfx->print(text);\n}\n\nstatic void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {\n  centerText(text, centerX, y, size, color);\n}\n'''
s = s[:start] + new_render_helpers + s[end:]

old_apparent = '''static void drawApparentTemperature(float apparentF) {\n  String value = String((int)lroundf(apparentF));\n  const bool threeDigits = value.length() >= 3;\n\n  if (threeDigits) {\n    printBoldAt(55, 122, value, C_WHITE, 4);\n    gfx->drawCircle(119, 123, 3, C_WHITE);\n    printBoldAt(125, 134, "F", C_WHITE, 2);\n  } else {\n    printBoldAt(57, 116, value, C_WHITE, 5);\n    gfx->drawCircle(118, 119, 3, C_WHITE);\n    printBoldAt(124, 132, "F", C_WHITE, 2);\n  }\n}\n'''
new_apparent = '''static void drawApparentTemperature(float apparentF) {\n  String value = String((int)lroundf(apparentF));\n  const bool threeDigits = value.length() >= 3;\n  const uint8_t valueSize = threeDigits ? 4 : 5;\n  const int valueX = threeDigits ? 50 : 57;\n  const int valueY = threeDigits ? 118 : 116;\n\n  setText(C_WHITE, valueSize);\n  int16_t x1, y1;\n  uint16_t valueW, valueH;\n  gfx->getTextBounds(value, 0, 0, &x1, &y1, &valueW, &valueH);\n  printBoldAt(valueX, valueY, value, C_WHITE, valueSize);\n\n  const int degreeX = valueX + (int)valueW + 4;\n  gfx->drawCircle(degreeX, valueY + 4, 2, C_WHITE);\n  printBoldAt(degreeX + 6, valueY + 8, "F", C_WHITE, 1);\n}\n'''
assert old_apparent in s, 'apparent temperature block not found'
s = s.replace(old_apparent, new_apparent, 1)

old_header_date = '''  setText(rgb565(219, 231, 238), 1);\n  String dateStr = currentDateText();\n  int16_t x1, y1;\n  uint16_t w, h;\n  gfx->getTextBounds(dateStr, 0, 0, &x1, &y1, &w, &h);\n  gfx->setCursor(229 - w, 18);\n  gfx->print(dateStr);\n'''
new_header_date = '''  setText(rgb565(219, 231, 238), 1);\n  String dateStr = currentDateText();\n  int16_t x1, y1;\n  uint16_t w, h;\n  gfx->getTextBounds(dateStr, 0, 0, &x1, &y1, &w, &h);\n  gfx->setCursor(229 - (int)w - x1, 18 - y1);\n  gfx->print(dateStr);\n'''
assert old_header_date in s, 'header date block not found'
s = s.replace(old_header_date, new_header_date, 1)

old_wind = '''  centerBoldText("WIND", 41, 214, 1, rgb565(157, 200, 228));\n  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 51, 228, 2, C_WHITE);\n  centerBoldText("mph", 51, 242, 1, muted);\n  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"),\n                 41, 251, 1, rgb565(166, 209, 234));\n  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"),\n                 41, 258, 1, rgb565(166, 209, 234));\n'''
new_wind = '''  centerBoldText("WIND MPH", 41, 214, 1, rgb565(157, 200, 228));\n  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 51, 228, 2, C_WHITE);\n  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"),\n                 41, 244, 1, rgb565(166, 209, 234));\n  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"),\n                 41, 253, 1, rgb565(166, 209, 234));\n'''
assert old_wind in s, 'wind card text block not found'
s = s.replace(old_wind, new_wind, 1)

s = s.replace('  centerBoldText("HIGH / LOW F", 188, 225, 1, muted);\n',
              '  centerBoldText("HIGH / LOW", 188, 225, 1, muted);\n', 1)

path.write_text(s)
