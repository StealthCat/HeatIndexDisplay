from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W_PATH = ROOT / "Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp"
README = ROOT / "README.md"
RELEASE = ROOT / "RELEASE_V7_11_6_WAVESHARE_APPARENT_ALIGNMENT.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Pattern not found for {label}")
    return text.replace(old, new, 1)


w = W_PATH.read_text(encoding="utf-8")

old = '''  String value = String((int)lroundf(apparentF));
  setText(C_WHITE, 5);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(value, 0, 0, &x1, &y1, &w, &h);
  int valX = 72 - (int)w / 2;
  gfx->setCursor(valX, 110);
  gfx->print(value);
  gfx->drawCircle(valX + w + 5, 111, 3, C_WHITE);

  setText(C_WHITE, 2);
  gfx->setCursor(valX + w + 12, 124);
  gfx->print("F");
'''

new = '''  String value = String((int)lroundf(apparentF));

  // Center the complete apparent-temperature group (value + degree mark + F),
  // not just the numeric value. Centering only the digits pushed the degree/F
  // pair against the right edge for three-digit heat indexes such as 100 F.
  setText(C_WHITE, 5);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(value, 0, 0, &x1, &y1, &w, &h);

  setText(C_WHITE, 2);
  int16_t fx1, fy1;
  uint16_t fw, fh;
  gfx->getTextBounds("F", 0, 0, &fx1, &fy1, &fw, &fh);

  const int degreeRadius = 3;
  const int valueDegreeGap = 4;
  const int degreeFGap = 4;
  const int groupWidth = (int)w + valueDegreeGap + (degreeRadius * 2) + degreeFGap + (int)fw;
  const int groupLeft = 74 - groupWidth / 2;

  setText(C_WHITE, 5);
  gfx->setCursor(groupLeft, 110);
  gfx->print(value);

  const int degreeX = groupLeft + (int)w + valueDegreeGap + degreeRadius;
  gfx->drawCircle(degreeX, 114, degreeRadius, C_WHITE);

  const int fX = degreeX + degreeRadius + degreeFGap;
  setText(C_WHITE, 2);
  gfx->setCursor(fX, 124);
  gfx->print("F");
'''

w = replace_once(w, old, new, "Waveshare apparent-temperature group alignment")
W_PATH.write_text(w, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
section = '''\n## V7.11.6 Waveshare apparent-temperature alignment\n\nThe Waveshare apparent-temperature value now centers the complete value/degree/F group rather than centering only the digits. This prevents three-digit heat-index values from pushing the degree marker and Fahrenheit label against the right side of the panel.\n'''
if "## V7.11.6 Waveshare apparent-temperature alignment" not in readme:
    README.write_text(readme.rstrip() + "\n" + section, encoding="utf-8")

RELEASE.write_text('''# V7.11.6 — Waveshare apparent-temperature alignment\n\nThis production fix corrects apparent-temperature alignment on the Waveshare ESP32-S3 Touch LCD 2.8.\n\nThe previous layout centered only the numeric digits and then appended the degree marker and `F`. With a three-digit heat index such as `100`, that pushed the unit pair too far right.\n\nV7.11.6 measures the numeric value and Fahrenheit glyph, calculates the width of the complete value + degree + F group, and centers that complete group inside the 128-pixel apparent-temperature panel. The degree marker is also given an explicit superscript position relative to the number.\n\nNo weather calculations, provider APIs, polling behavior, forecast behavior, or LILYGO layout are changed.\n''', encoding="utf-8")
