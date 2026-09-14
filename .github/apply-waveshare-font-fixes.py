from pathlib import Path
import hashlib
import json

ROOT = Path('.')


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected one match, found {count}')
    path.write_text(text.replace(old, new, 1))


# ---------------------------------------------------------------------------
# Use the same ESP32-safe ASCII date/time formatting approach as T-Display.
# Preserve the Waveshare header's date-only content while removing unsupported
# %-I / %-d strftime modifiers that can render garbage on ESP32 libc builds.
# ---------------------------------------------------------------------------
for rel in (
    'Waveshare-ESP32-S3-Touch-LCD-2.8/src/time_utils.cpp',
    'Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/time_utils.cpp',
):
    path = ROOT / rel
    replace_once(
        path,
        '''String formatClockFromEpoch(time_t t) {
  if (t <= 100000) return "--:--";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  char buf[16];
  strftime(buf, sizeof(buf), "%-I:%M %p", &timeinfo);
  return String(buf);
}
''',
        '''String formatClockFromEpoch(time_t t) {
  if (t <= 100000) return "--:--";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  int hour = timeinfo.tm_hour % 12;
  if (hour == 0) hour = 12;
  char buf[16];
  snprintf(buf, sizeof(buf), "%d:%02d %s", hour, timeinfo.tm_min,
           timeinfo.tm_hour < 12 ? "AM" : "PM");
  return String(buf);
}
''')
    replace_once(
        path,
        '''String formatDateFromEpoch(time_t t) {
  if (t <= 100000) return "";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  char buf[32];
  strftime(buf, sizeof(buf), "%a, %b %-d, %Y", &timeinfo);
  return String(buf);
}
''',
        '''String formatDateFromEpoch(time_t t) {
  if (t <= 100000) return "";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  static const char *WEEKDAYS[] = {
    "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"
  };
  static const char *MONTHS[] = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
  };
  const int weekday = (timeinfo.tm_wday >= 0 && timeinfo.tm_wday < 7)
    ? timeinfo.tm_wday : 0;
  const int month = (timeinfo.tm_mon >= 0 && timeinfo.tm_mon < 12)
    ? timeinfo.tm_mon : 0;
  char buf[32];
  snprintf(buf, sizeof(buf), "%s, %s %d, %d", WEEKDAYS[weekday],
           MONTHS[month], timeinfo.tm_mday, timeinfo.tm_year + 1900);
  return String(buf);
}
''')


# ---------------------------------------------------------------------------
# Waveshare 2.8: eliminate font-dependent degree glyphs. Draw the degree mark
# geometrically, as the T-Display now does.
# ---------------------------------------------------------------------------
p28 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp'
replace_once(
    p28,
    '''String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s;
  if (value >= 0.0f) s += "+";
  s += String(value, 1);
  s += String((char)247);
  s += "F";
  return s;
}
''',
    '''String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s;
  if (value >= 0.0f) s += "+";
  s += String(value, 1);
  return s;
}
''')

replace_once(
    p28,
    '''static void printTempValueCompact(int x, int y, float value) {
  if (!isfinite(value)) {
    printBoldAt(x, y, "--", C_WHITE, 2);
    return;
  }

  String number = String(value, 1);
  setText(C_WHITE, 2);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(number, 0, 0, &x1, &y1, &w, &h);
  printBoldAt(x, y, number, C_WHITE, 2);
  printBoldAt(x + (int)w + 1, y + 7, String((char)247) + "F", C_WHITE, 1);
}
''',
    '''static void printTempValueCompact(int x, int y, float value) {
  if (!isfinite(value)) {
    printBoldAt(x, y, "--", C_WHITE, 2);
    return;
  }

  String number = String(value, 1);
  setText(C_WHITE, 2);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(number, 0, 0, &x1, &y1, &w, &h);
  printBoldAt(x, y, number, C_WHITE, 2);
  gfx->drawCircle(x + (int)w + 3, y + 3, 2, C_WHITE);
  printBoldAt(x + (int)w + 7, y + 7, "F", C_WHITE, 1);
}

static void printSignedTempValueCompact(int x, int y, float value) {
  if (!isfinite(value)) {
    printBoldAt(x, y, "--", C_WHITE, 1);
    return;
  }

  String number = signedTempDelta(value);
  setText(C_WHITE, 1);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(number, 0, 0, &x1, &y1, &w, &h);
  printBoldAt(x, y, number, C_WHITE, 1);
  gfx->drawCircle(x + (int)w + 2, y + 2, 1, C_WHITE);
  printBoldAt(x + (int)w + 5, y, "F", C_WHITE, 1);
}
''')

replace_once(
    p28,
    '  printBoldAt(169, 186, signedTempDelta(wx.fromYesterdayF), C_WHITE, 1);\n',
    '  printSignedTempValueCompact(169, 186, wx.fromYesterdayF);\n')

replace_once(
    p28,
    '''    String highText = String((int)lroundf(high)) + String((char)247);
    String lowText = String((int)lroundf(low)) + String((char)247);
    printBoldAt(148, 239, highText, C_WHITE, 2);
    printBoldAt(183, 245, "/", C_WHITE, 1);
    printBoldAt(192, 239, lowText, C_WHITE, 2);
''',
    '''    String highText = String((int)lroundf(high));
    String lowText = String((int)lroundf(low));
    setText(C_WHITE, 2);
    int16_t x1, y1;
    uint16_t highW, textH, lowW;
    gfx->getTextBounds(highText, 0, 0, &x1, &y1, &highW, &textH);
    gfx->getTextBounds(lowText, 0, 0, &x1, &y1, &lowW, &textH);
    printBoldAt(148, 239, highText, C_WHITE, 2);
    gfx->drawCircle(148 + (int)highW + 3, 242, 2, C_WHITE);
    printBoldAt(183, 245, "/", C_WHITE, 1);
    printBoldAt(192, 239, lowText, C_WHITE, 2);
    gfx->drawCircle(192 + (int)lowW + 3, 242, 2, C_WHITE);
''')


# ---------------------------------------------------------------------------
# Waveshare 7C: same degree-glyph fix for metric cards, forecast and compass.
# ---------------------------------------------------------------------------
p7 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp'
replace_once(
    p7,
    '''static String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s; if (value >= 0.0f) s += "+";
  s += String(value, 1); s += String((char)247); s += "F";
  return s;
}
''',
    '''static String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s; if (value >= 0.0f) s += "+";
  s += String(value, 1);
  return s;
}
''')

replace_once(
    p7,
    '''static void drawMetricCardValue(int x, int y, int w, int h, const uint16_t *iconData,
                                const String &label, const String &value, uint8_t valueSize = 3) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 12, false);
  drawIconBitmapScaled(x + 12, y + (h - 40) / 2, iconData, 2);
  printBoldAt(x + 64, y + 9, label, cyan, 2);
  printBoldAt(x + 64, y + 27, value, C_WHITE, valueSize);
}
''',
    '''static void drawMetricCardValue(int x, int y, int w, int h, const uint16_t *iconData,
                                const String &label, const String &value, uint8_t valueSize = 3) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 12, false);
  drawIconBitmapScaled(x + 12, y + (h - 40) / 2, iconData, 2);
  printBoldAt(x + 64, y + 9, label, cyan, 2);
  printBoldAt(x + 64, y + 27, value, C_WHITE, valueSize);
}

static void drawMetricCardTemperatureValue(int x, int y, int w, int h,
                                           const uint16_t *iconData,
                                           const String &label, float value,
                                           bool signedValue = false) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 12, false);
  drawIconBitmapScaled(x + 12, y + (h - 40) / 2, iconData, 2);
  printBoldAt(x + 64, y + 9, label, cyan, 2);
  if (!isfinite(value)) {
    printBoldAt(x + 64, y + 27, "--", C_WHITE, 3);
    return;
  }

  String number;
  if (signedValue && value >= 0.0f) number += "+";
  number += String(value, 1);
  setText(C_WHITE, 3);
  int16_t x1, y1;
  uint16_t numberW, numberH;
  gfx->getTextBounds(number, 0, 0, &x1, &y1, &numberW, &numberH);
  const int valueX = x + 64;
  const int valueY = y + 27;
  printBoldAt(valueX, valueY, number, C_WHITE, 3);
  gfx->drawCircle(valueX + (int)numberW + 5, valueY + 6, 3, C_WHITE);
  printBoldAt(valueX + (int)numberW + 11, valueY + 8, "F", C_WHITE, 2);
}
''')

replace_once(
    p7,
    '''    String value = String((int)lroundf(high)) + String((char)247) + " / " + String((int)lroundf(low)) + String((char)247);
    centerBoldText(value, 635, 355, 4, C_WHITE);
''',
    '''    String highText = String((int)lroundf(high));
    String lowText = String((int)lroundf(low));
    setText(C_WHITE, 4);
    int16_t x1, y1;
    uint16_t highW, textH, lowW, slashW;
    gfx->getTextBounds(highText, 0, 0, &x1, &y1, &highW, &textH);
    gfx->getTextBounds(lowText, 0, 0, &x1, &y1, &lowW, &textH);
    gfx->getTextBounds("/", 0, 0, &x1, &y1, &slashW, &textH);
    const int degreeSlot = 13;
    const int gap = 8;
    const int groupW = (int)highW + degreeSlot + gap + (int)slashW + gap +
                       (int)lowW + degreeSlot;
    int valueX = 635 - groupW / 2;
    printBoldAt(valueX, 355, highText, C_WHITE, 4);
    gfx->drawCircle(valueX + (int)highW + 5, 361, 3, C_WHITE);
    valueX += (int)highW + degreeSlot + gap;
    printBoldAt(valueX, 355, "/", C_WHITE, 4);
    valueX += (int)slashW + gap;
    printBoldAt(valueX, 355, lowText, C_WHITE, 4);
    gfx->drawCircle(valueX + (int)lowW + 5, 361, 3, C_WHITE);
''')

replace_once(
    p7,
    '''  drawMetricCardValue(477, 82, 290, 50, ICON_THERMOMETER, "TEMP", isfinite(wx.tempF) ? String(wx.tempF, 1) + String((char)247) + "F" : "--");
  drawMetricCardValue(477, 137, 290, 50, ICON_DROP, "HUMIDITY", isfinite(wx.humidity) ? String((int)lroundf(wx.humidity)) + "%" : "--");
  drawMetricCardValue(477, 192, 290, 50, ICON_LEAF, "DEW POINT", isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String((char)247) + "F" : "--");
  drawMetricCardValue(477, 247, 290, 60, ICON_TREND, "FROM YDAY", signedTempDelta(wx.fromYesterdayF));
''',
    '''  drawMetricCardTemperatureValue(477, 82, 290, 50, ICON_THERMOMETER, "TEMP", wx.tempF);
  drawMetricCardValue(477, 137, 290, 50, ICON_DROP, "HUMIDITY", isfinite(wx.humidity) ? String((int)lroundf(wx.humidity)) + "%" : "--");
  drawMetricCardTemperatureValue(477, 192, 290, 50, ICON_LEAF, "DEW POINT", wx.dewPointF);
  drawMetricCardTemperatureValue(477, 247, 290, 60, ICON_TREND, "FROM YDAY", wx.fromYesterdayF, true);
''')

replace_once(
    p7,
    '''  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg)) + String((char)247);
    centerBoldText(dirNumber, 385, 345, 4, C_WHITE);
    centerBoldText(directionText(wx.windDirDeg), 356, 376, 2, rgb565(157, 200, 228));
  } else {
''',
    '''  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg));
    setText(C_WHITE, 4);
    int16_t x1, y1;
    uint16_t dirW, dirH;
    gfx->getTextBounds(dirNumber, 0, 0, &x1, &y1, &dirW, &dirH);
    const int groupW = (int)dirW + 13;
    const int startX = 385 - groupW / 2;
    printBoldAt(startX, 345, dirNumber, C_WHITE, 4);
    gfx->drawCircle(startX + (int)dirW + 5, 351, 3, C_WHITE);
    centerBoldText(directionText(wx.windDirDeg), 356, 376, 2, rgb565(157, 200, 228));
  } else {
''')

for path in (p28, p7):
    if '(char)247' in path.read_text():
        raise SystemExit(f'{path}: font-dependent degree glyph remains')

# Refresh every pinned firmware hash so the manifest reflects the actual main
# tree rather than leaving previously stale source pins behind.
manifest_path = ROOT / '.github/concept1-emulator-v7.11.10-manifest.json'
manifest = json.loads(manifest_path.read_text())
for rel in manifest.get('firmware_sources', {}):
    file_path = ROOT / rel
    if not file_path.exists():
        raise SystemExit(f'Manifest-pinned firmware file missing: {rel}')
    manifest['firmware_sources'][rel] = hashlib.sha256(file_path.read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')

print('Applied Waveshare font/date/degree fixes and refreshed firmware pins.')
