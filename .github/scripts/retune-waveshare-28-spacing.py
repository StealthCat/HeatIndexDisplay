from pathlib import Path

path = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
s = path.read_text()

replacements = []

old = '''  printBoldAt(169, 97, "HUMIDITY", cyan, 1);
  printBoldAt(169, 109, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);

  drawConceptCard(143, 128, 87, 34, 7, false);
  drawLeaf(157, 145, green);
  printBoldAt(169, 134, "DEW POINT", cyan, 1);
  printTempValueCompact(169, 146, wx.dewPointF);

  drawConceptCard(143, 165, 87, 40, 7, false);
  drawTrend(148, 176, cyan);
  printBoldAt(169, 171, "FROM YDAY", cyan, 1);
  printSignedTempValueCompact(169, 186, wx.fromYesterdayF);
'''
new = '''  printBoldAt(169, 97, "HUMID", cyan, 1);
  printBoldAt(169, 109, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);

  drawConceptCard(143, 128, 87, 34, 7, false);
  drawLeaf(157, 145, green);
  printBoldAt(169, 134, "DEW PT", cyan, 1);
  printTempValueCompact(169, 146, wx.dewPointF);

  drawConceptCard(143, 165, 87, 40, 7, false);
  drawTrend(148, 176, cyan);
  printBoldAt(169, 171, "VS YDAY", cyan, 1);
  printSignedTempValueCompact(169, 186, wx.fromYesterdayF);
'''
replacements.append((old, new, 'right metric labels'))

old = '''void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 182, 198);
  const uint16_t cyan = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();

  drawConceptCard(143, 210, 87, 52, 8, true);
  drawSunIcon(160, 237, rgb565(255, 193, 43));

  centerBoldText(tomorrow ? "TOMORROW" : "TODAY", 188, 214, 1, cyan);
  centerBoldText("HIGH / LOW F", 188, 225, 1, muted);

  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
  if (wx.forecastValid && isfinite(high) && isfinite(low)) {
    String highText = String((int)lroundf(high));
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
  } else {
    centerBoldText("-- / --", 190, 239, 2, C_WHITE);
  }
}
'''
new = '''void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 182, 198);
  const uint16_t cyan = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();

  drawConceptCard(143, 210, 87, 52, 8, true);
  centerBoldText(tomorrow ? "TOMORROW" : "TODAY", 188, 214, 1, cyan);
  centerBoldText("HIGH", 164, 225, 1, muted);
  centerBoldText("LOW", 207, 225, 1, muted);

  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
  if (wx.forecastValid && isfinite(high) && isfinite(low)) {
    String highText = String((int)lroundf(high));
    String lowText = String((int)lroundf(low));
    setText(C_WHITE, 2);
    int16_t x1, y1;
    uint16_t highW, textH, lowW;
    gfx->getTextBounds(highText, 0, 0, &x1, &y1, &highW, &textH);
    gfx->getTextBounds(lowText, 0, 0, &x1, &y1, &lowW, &textH);

    int highX = 164 - ((int)highW + 7) / 2;
    int lowX = 207 - ((int)lowW + 7) / 2;
    printBoldAt(highX, 239, highText, C_WHITE, 2);
    gfx->drawCircle(highX + (int)highW + 3, 241, 2, C_WHITE);
    printBoldAt(lowX, 239, lowText, C_WHITE, 2);
    gfx->drawCircle(lowX + (int)lowW + 3, 241, 2, C_WHITE);
  } else {
    centerBoldText("--", 164, 239, 2, C_WHITE);
    centerBoldText("--", 207, 239, 2, C_WHITE);
  }
}
'''
replacements.append((old, new, 'forecast card'))

old = '''  // Bottom three cards.
  drawConceptCard(10, 210, 62, 52, 8, true);
  drawWindIcon(15, 226, cyan);
  centerBoldText("WIND", 41, 214, 1, rgb565(157, 200, 228));
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 51, 228, 2, C_WHITE);
  centerBoldText("mph", 51, 242, 1, muted);
  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"),
                 41, 251, 1, rgb565(166, 209, 234));
  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"),
                 41, 258, 1, rgb565(166, 209, 234));

  drawConceptCard(76, 210, 62, 52, 8, true);
  drawCompassIcon(88, 236, cyan);
  centerBoldText("DIRECTION", 107, 214, 1, rgb565(157, 200, 228));
  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg));
    centerBoldText(dirNumber, 116, 229, 2, C_WHITE);
    gfx->drawCircle(135, 231, 2, C_WHITE);
  } else {
    centerBoldText("--", 116, 229, 2, C_WHITE);
  }
  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--",
                 107, 250, 1, rgb565(157, 200, 228));
'''
new = '''  // Bottom cards use short labels and centered values so adjacent cards do not
  // visually run together on the 240-pixel-wide panel.
  drawConceptCard(10, 210, 62, 52, 8, true);
  centerBoldText("WIND", 41, 214, 1, rgb565(157, 200, 228));
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 41, 227, 2, C_WHITE);
  centerBoldText("MPH", 41, 243, 1, muted);
  String windSummary = String("G") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--") +
                       " M" + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--");
  centerBoldText(windSummary, 41, 253, 1, rgb565(166, 209, 234));

  drawConceptCard(76, 210, 62, 52, 8, true);
  centerBoldText("DIR", 107, 214, 1, rgb565(157, 200, 228));
  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg));
    setText(C_WHITE, 2);
    int16_t x1, y1;
    uint16_t dirW, dirH;
    gfx->getTextBounds(dirNumber, 0, 0, &x1, &y1, &dirW, &dirH);
    int dirX = 107 - ((int)dirW + 7) / 2;
    printBoldAt(dirX, 229, dirNumber, C_WHITE, 2);
    gfx->drawCircle(dirX + (int)dirW + 3, 231, 2, C_WHITE);
  } else {
    centerBoldText("--", 107, 229, 2, C_WHITE);
  }
  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--",
                 107, 248, 1, rgb565(157, 200, 228));
'''
replacements.append((old, new, 'bottom cards'))

old = '''  const bool offline = !wx.valid;
  const bool stale = !offline && dataStale();
  const uint16_t stateColor = offline ? red : (stale ? red : green);
  drawClockIcon(24, 290, muted);

  String left;
  String state;
  uint16_t leftColor = C_WHITE;
  int leftX = 45;
'''
new = '''  const bool offline = !wx.valid;
  const bool stale = !offline && dataStale();
  const uint16_t stateColor = offline ? red : (stale ? red : green);
  drawClockIcon(23, 290, muted);

  String left;
  String state;
  uint16_t leftColor = C_WHITE;
  int leftX = 39;
'''
replacements.append((old, new, 'footer left spacing'))

old = '''  // Preserve the LILYGO visual contract: 4 px from dot edge to label.
  gfx->drawFastVLine(151, 280, 20, rgb565(85, 115, 133));
  gfx->fillCircle(172, 290, 3, stateColor);
  printBoldAt(179, 286, state, stateColor, 1);
'''
new = '''  // Keep the state visually separate from the update time while preserving a
  // 4 px dot-to-label gap.
  gfx->drawFastVLine(150, 280, 20, rgb565(85, 115, 133));
  gfx->fillCircle(164, 290, 3, stateColor);
  printBoldAt(171, 286, state, stateColor, 1);
'''
replacements.append((old, new, 'footer state spacing'))

for old, new, name in replacements:
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{name}: expected exactly 1 match, found {count}')
    s = s.replace(old, new)

path.write_text(s)
