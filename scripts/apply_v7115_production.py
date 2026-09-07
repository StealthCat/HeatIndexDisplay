from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T_PATH = ROOT / "T-Display-S3/src/display_ui.cpp"
W_PATH = ROOT / "Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp"
README = ROOT / "README.md"
RELEASE = ROOT / "RELEASE_V7_11_5_PRODUCTION_DISPLAY_REFINEMENT.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Pattern not found for {label}")
    return text.replace(old, new, 1)


# -----------------------------------------------------------------------------
# LILYGO T-Display S3
# -----------------------------------------------------------------------------
t = T_PATH.read_text(encoding="utf-8")

# Valid-data footer: Updated on the left, ONLINE/STALE on the right.
t = replace_once(
    t,
    '''  String footer = "Updated ";
  footer += updateClockText();
  if (dataStale()) {
    footer = "STALE - " + footer;
    display.setTextColor(rgb565(255, 105, 90), bg);
  }
  display.drawString(footer, 85, 305);
''',
    '''  String footer = "Updated ";
  footer += updateClockText();
  const bool stale = dataStale();

  display.setTextDatum(textdatum_t::middle_left);
  display.setTextColor(stale ? rgb565(255, 105, 90) : C_WHITE, bg);
  display.drawString(footer, 14, 305);

  display.setTextDatum(textdatum_t::middle_right);
  display.setTextColor(stale ? rgb565(255, 105, 90) : rgb565(80, 225, 110), bg);
  display.drawString(stale ? "STALE" : "ONLINE", 156, 305);

  display.setTextDatum(textdatum_t::middle_center);
''',
    "T-Display footer status",
)

# Center icons vertically in their small cards and normalize the card text rhythm.
for old, new, label in [
    ('drawThermometer(13, 153, rgb565(255, 70, 55));',
     'drawThermometer(13, 154, rgb565(255, 70, 55));', 'T temp icon'),
    ('drawBoldText("TEMP", 29, 157, cyan);',
     'drawBoldText("TEMP", 31, 157, cyan);', 'T temp label'),
    ('drawBoldText(String(wx.tempF, 1) + String("\\xB0") + "F", 29, 173, C_WHITE);',
     'drawBoldText(String(wx.tempF, 1) + String("\\xB0") + "F", 31, 171, C_WHITE);', 'T temp value'),

    ('drawDrop(99, 153, rgb565(50, 165, 255));',
     'drawDrop(99, 154, rgb565(50, 165, 255));', 'T humidity icon'),
    ('drawBoldText(String((int)lroundf(wx.humidity)) + "%", 113, 173, C_WHITE);',
     'drawBoldText(String((int)lroundf(wx.humidity)) + "%", 113, 171, C_WHITE);', 'T humidity value'),

    ('drawLeafIcon(19, 198, green);',
     'drawLeafIcon(19, 201, green);', 'T dew icon'),
    ('drawBoldText(isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String("\\xB0") + "F" : "--", 31, 210, C_WHITE);',
     'drawBoldText(isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String("\\xB0") + "F" : "--", 31, 208, C_WHITE);', 'T dew value'),

    ('drawTrendIcon(94, 195, cyan);',
     'drawTrendIcon(94, 191, cyan);', 'T yesterday icon'),
    ('drawBoldText(signedTempDelta(wx.fromYesterdayF), 113, 210, C_WHITE);',
     'drawBoldText(signedTempDelta(wx.fromYesterdayF), 113, 208, C_WHITE);', 'T yesterday value'),

    ('drawWindIcon(13, 232, cyan);',
     'drawWindIcon(13, 230, cyan);', 'T wind icon'),
    ('drawBoldText(windLine, 34, 242, C_WHITE);',
     'drawBoldText(windLine, 31, 245, C_WHITE);', 'T wind value'),

    ('drawBoldText("DIR", 115, 231, cyan);',
     'drawBoldText("DIR", 113, 231, cyan);', 'T direction label'),
    ('drawBoldText(dirLine, 115, 248, C_WHITE);',
     'drawBoldText(dirLine, 113, 245, C_WHITE);', 'T direction value'),
]:
    t = replace_once(t, old, new, label)

T_PATH.write_text(t, encoding="utf-8")


# -----------------------------------------------------------------------------
# Waveshare ESP32-S3 Touch LCD 2.8
# -----------------------------------------------------------------------------
w = W_PATH.read_text(encoding="utf-8")

# Forecast card: shorter bottom row, centered sun, larger/repositioned temperatures.
w = replace_once(
    w,
    '''  drawRoundedRectCard(143, 201, 87, 68);
  drawSunIcon(157, 236, yellow);

  printBoldAt(174, 207, tomorrow ? "TOMORROW" : "TODAY", cyan, 1);
  printBoldAt(174, 219, "HIGH / LOW F", muted, 1);
''',
    '''  drawRoundedRectCard(143, 217, 87, 48);
  drawSunIcon(157, 241, yellow);

  printBoldAt(174, 219, tomorrow ? "TOMORROW" : "TODAY", cyan, 1);
  printBoldAt(174, 229, "HIGH / LOW F", muted, 1);
''',
    "Waveshare forecast geometry",
)

w = replace_once(
    w,
    '''    printBoldAt(146, 239, highText, C_WHITE, 2);
    printBoldAt(183, 244, " / ", C_WHITE, 1);
    printBoldAt(191, 239, lowText, C_WHITE, 2);
  } else {
    printBoldAt(166, 239, "-- / --", C_WHITE, 2);
''',
    '''    // Text size 2 is the largest classic-font scale that allows both
    // degree-marked temperatures to fit this 87-pixel card. Spread the two
    // values across the available width and keep the slash visually centered.
    printBoldAt(148, 241, highText, C_WHITE, 2);
    printBoldAt(183, 246, " / ", C_WHITE, 1);
    printBoldAt(192, 241, lowText, C_WHITE, 2);
  } else {
    printBoldAt(166, 241, "-- / --", C_WHITE, 2);
''',
    "Waveshare forecast temperatures",
)

# Enlarge the main apparent card and the four right-side metric cards.
w = replace_once(
    w,
    '''  gfx->fillRoundRect(10, 65, 128, 128, 12, risk.panel);
  centerBoldText(apparentTitle(), 74, 78, 2, C_WHITE);
''',
    '''  gfx->fillRoundRect(10, 65, 128, 148, 12, risk.panel);
  centerBoldText(apparentTitle(), 74, 80, 2, C_WHITE);
''',
    "Waveshare main card height",
)
w = replace_once(w, '  gfx->setCursor(valX, 105);', '  gfx->setCursor(valX, 110);', 'Waveshare apparent value y')
w = replace_once(w, '  gfx->drawCircle(valX + w + 5, 106, 3, C_WHITE);', '  gfx->drawCircle(valX + w + 5, 111, 3, C_WHITE);', 'Waveshare apparent degree y')
w = replace_once(w, '  gfx->setCursor(valX + w + 12, 119);', '  gfx->setCursor(valX + w + 12, 124);', 'Waveshare apparent F y')
w = replace_once(
    w,
    '''  gfx->fillRoundRect(22, 154, 104, 25, 7, risk.status);
  centerBoldText(apparentRiskLabel(), 74, 162, 1, C_WHITE);
''',
    '''  gfx->fillRoundRect(18, 177, 112, 24, 7, risk.status);
  centerBoldText(apparentRiskLabel(), 74, 184, 1, C_WHITE);
''',
    "Waveshare risk box",
)

# Four taller metric cards and their text/icon placement.
for old, new, label in [
    ('drawRoundedRectCard(143, 65, 87, 29);', 'drawRoundedRectCard(143, 65, 87, 36);', 'W temp card'),
    ('drawThermometer(150, 68, rgb565(255, 70, 55));', 'drawThermometer(150, 73, rgb565(255, 70, 55));', 'W temp icon'),
    ('printBoldAt(169, 69, "TEMP", cyan, 1);', 'printBoldAt(169, 76, "TEMP", cyan, 1);', 'W temp label'),
    ('printBoldAt(169, 79, String(wx.tempF, 1) + String((char)247) + "F", C_WHITE, 2);', 'printBoldAt(169, 91, String(wx.tempF, 1) + String((char)247) + "F", C_WHITE, 2);', 'W temp value'),

    ('drawRoundedRectCard(143, 98, 87, 29);', 'drawRoundedRectCard(143, 102, 87, 36);', 'W humidity card'),
    ('drawDrop(158, 101, rgb565(50, 165, 255));', 'drawDrop(158, 110, rgb565(50, 165, 255));', 'W humidity icon'),
    ('printBoldAt(169, 102, "HUMIDITY", cyan, 1);', 'printBoldAt(169, 113, "HUMIDITY", cyan, 1);', 'W humidity label'),
    ('printBoldAt(169, 112, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);', 'printBoldAt(169, 128, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);', 'W humidity value'),

    ('drawRoundedRectCard(143, 131, 87, 29);', 'drawRoundedRectCard(143, 139, 87, 36);', 'W dew card'),
    ('drawLeaf(157, 145, green);', 'drawLeaf(157, 157, green);', 'W dew icon'),
    ('printBoldAt(169, 135, "DEW POINT", cyan, 1);', 'printBoldAt(169, 150, "DEW POINT", cyan, 1);', 'W dew label'),
    ('printBoldAt(169, 145, isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String((char)247) + "F" : "--", C_WHITE, 2);', 'printBoldAt(169, 165, isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String((char)247) + "F" : "--", C_WHITE, 2);', 'W dew value'),

    ('drawRoundedRectCard(143, 164, 87, 29);', 'drawRoundedRectCard(143, 176, 87, 36);', 'W yday card'),
    ('drawTrend(149, 170, cyan);', 'drawTrend(149, 186, cyan);', 'W yday icon'),
    ('printBoldAt(169, 168, "FROM YDAY", cyan, 1);', 'printBoldAt(169, 187, "FROM YDAY", cyan, 1);', 'W yday label'),
    ('printBoldAt(169, 180, signedTempDelta(wx.fromYesterdayF), C_WHITE, 1);', 'printBoldAt(169, 202, signedTempDelta(wx.fromYesterdayF), C_WHITE, 1);', 'W yday value'),
]:
    w = replace_once(w, old, new, label)

# Shorter bottom row. Full-size 20x20 icons are vertically centered at y=241.
w = replace_once(w, '  drawRoundedRectCard(10, 201, 62, 68);', '  drawRoundedRectCard(10, 217, 62, 48);', 'W wind card')
w = replace_once(w, '  drawWindIcon(16, 223, cyan);', '  drawWindIcon(16, 233, cyan);', 'W wind icon')
w = replace_once(w, '  centerBoldText("WIND", 41, 205, 1, cyan);', '  centerBoldText("WIND", 41, 219, 1, cyan);', 'W wind label')
w = replace_once(w, '  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 53, 220, 2, C_WHITE);', '  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 53, 229, 2, C_WHITE);', 'W wind value')
w = replace_once(w, '  centerBoldText("mph", 53, 239, 1, muted);', '  centerBoldText("mph", 53, 243, 1, muted);', 'W mph')
w = replace_once(w, '  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"), 41, 250, 1, cyan);', '  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"), 41, 251, 1, cyan);', 'W gust')
w = replace_once(w, '  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"), 41, 259, 1, cyan);', '  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"), 41, 258, 1, cyan);', 'W max gust')

w = replace_once(w, '  drawRoundedRectCard(76, 201, 62, 68);', '  drawRoundedRectCard(76, 217, 62, 48);', 'W direction card')
w = replace_once(w, '  drawCompassIcon(92, 230, cyan);', '  drawCompassIcon(92, 241, cyan);', 'W compass icon')
w = replace_once(w, '  centerBoldText("DIRECTION", 107, 205, 1, cyan);', '  centerBoldText("DIRECTION", 107, 219, 1, cyan);', 'W direction label')
w = replace_once(w, '  centerBoldText(degText, 108, 221, 2, C_WHITE);', '  centerBoldText(degText, 116, 233, 2, C_WHITE);', 'W direction bearing')
w = replace_once(w, '  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--", 107, 247, 1, cyan);', '  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--", 107, 253, 1, cyan);', 'W cardinal direction')

W_PATH.write_text(w, encoding="utf-8")


# -----------------------------------------------------------------------------
# Documentation
# -----------------------------------------------------------------------------
release_text = '''# V7.11.5 — Production display refinement\n\nThis release promotes the emulator-approved V7.11.2–V7.11.5 display refinements to both production firmware targets.\n\n## LILYGO T-Display S3\n\n- Small metric cards use a consistent Dew-Point-style label/value rhythm.\n- Non-forecast values are nudged upward for better optical alignment.\n- Metric icons are vertically centered within their cards.\n- The footer now shows `Updated <time>` at left and `ONLINE` / `STALE` at right.\n- Forecast card behavior and its 30-second Today/Tomorrow switching are unchanged.\n\n## Waveshare ESP32-S3 Touch LCD 2.8\n\n- The main apparent-temperature card is taller.\n- All four upper metric cards are taller and reflowed into the reclaimed space.\n- Wind, Direction, and Forecast cards are reduced to a shorter 48-pixel row.\n- Wind and direction icons are centered vertically in the shorter cards.\n- The direction bearing is lowered to visually align with the compass icon.\n- Forecast high/low values remain at the largest classic-font scale that fits both degree-marked values in the card.\n- All existing provider, historical REST, forecast, stale-state, and polling behavior is unchanged.\n'''
RELEASE.write_text(release_text, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
section = '''\n## V7.11.5 production display refinement\n\nThe emulator-approved display refinements have been promoted to production for both boards. LILYGO gains aligned metric cards and ONLINE/STALE footer status; Waveshare reallocates vertical space from the bottom Wind/Direction/Forecast row to the main and upper metric cards, while aligning the direction bearing with the compass and retaining the large forecast presentation. See `RELEASE_V7_11_5_PRODUCTION_DISPLAY_REFINEMENT.md`.\n'''
if "## V7.11.5 production display refinement" not in readme:
    README.write_text(readme.rstrip() + "\n" + section, encoding="utf-8")

print("V7.11.5 production display migration applied")
