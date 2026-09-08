from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# LILYGO T-Display S3
path = Path("T-Display-S3/src/display_ui.cpp")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''static void drawAlertTriangle(int cx, int cy, uint16_t color) {
  display.fillTriangle(cx, cy - 6, cx - 6, cy + 5, cx + 6, cy + 5, color);
  display.drawFastVLine(cx, cy - 2, 4, C_BLACK);
  display.fillCircle(cx, cy + 3, 1, C_BLACK);
}

''',
    "",
    "T-Display remove alert helper",
)
text = replace_once(
    text,
    '''  display.fillRoundRect(16, 116, 138, 20, 10, risk.status);
  display.drawRoundRect(16, 116, 138, 20, 10, risk.accent);
  drawAlertTriangle(31, 126, risk.accent);
  display.setFont(&fonts::Font0);
  drawBoldText(apparentRiskLabel(), 90, 126, risk.accent);
''',
    '''  display.fillRoundRect(16, 116, 138, 20, 10, risk.status);
  display.drawRoundRect(16, 116, 138, 20, 10, risk.accent);
  display.setFont(&fonts::Font0);
  drawBoldText(apparentRiskLabel(), 85, 126, risk.accent);
''',
    "T-Display center risk label",
)
path.write_text(text, encoding="utf-8")


# Waveshare ESP32-S3 Touch LCD 2.8
path = Path("Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''static void drawAlertTriangle(int cx, int cy, uint16_t color) {
  gfx->fillTriangle(cx, cy - 7, cx - 7, cy + 6, cx + 7, cy + 6, color);
  gfx->drawFastVLine(cx, cy - 2, 5, C_BLACK);
  gfx->fillCircle(cx, cy + 4, 1, C_BLACK);
}

''',
    "",
    "Waveshare remove alert helper",
)
text = replace_once(
    text,
    '''  gfx->fillRoundRect(18, 170, 112, 24, 12, risk.status);
  gfx->drawRoundRect(18, 170, 112, 24, 12, risk.accent);
  drawAlertTriangle(32, 182, risk.accent);
  centerBoldText(apparentRiskLabel(), 85, 179, 1, risk.accent);
''',
    '''  gfx->fillRoundRect(18, 170, 112, 24, 12, risk.status);
  gfx->drawRoundRect(18, 170, 112, 24, 12, risk.accent);
  centerBoldText(apparentRiskLabel(), 74, 179, 1, risk.accent);
''',
    "Waveshare center risk label",
)
path.write_text(text, encoding="utf-8")

print("Applied centered Concept 1 risk-pill labels to both production targets.")
