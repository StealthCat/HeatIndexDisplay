from pathlib import Path

p = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
s = p.read_text()

old = '''void drawForecastHighLowCard() {
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
new = '''void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 182, 198);
  const uint16_t cyan = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();

  // Give the forecast card its own clean two-column hierarchy. The abbreviated
  // title and labels leave enough room for the large values on a 240 px panel.
  drawConceptCard(154, 210, 76, 52, 8, true);
  centerBoldText(tomorrow ? "TMRW" : "TODAY", 192, 214, 1, cyan);
  centerBoldText("HI", 173, 227, 1, muted);
  centerBoldText("LO", 211, 227, 1, muted);

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

    int highX = 173 - ((int)highW + 7) / 2;
    int lowX = 211 - ((int)lowW + 7) / 2;
    printBoldAt(highX, 239, highText, C_WHITE, 2);
    gfx->drawCircle(highX + (int)highW + 3, 241, 2, C_WHITE);
    printBoldAt(lowX, 239, lowText, C_WHITE, 2);
    gfx->drawCircle(lowX + (int)lowW + 3, 241, 2, C_WHITE);
  } else {
    centerBoldText("--", 173, 239, 2, C_WHITE);
    centerBoldText("--", 211, 239, 2, C_WHITE);
  }
}
'''
assert s.count(old) == 1, 'forecast block mismatch'
s = s.replace(old, new)

old = '''  // Keep the state visually separate from the update time while preserving a
  // 4 px dot-to-label gap.
  gfx->drawFastVLine(150, 280, 20, rgb565(85, 115, 133));
  gfx->fillCircle(164, 290, 3, stateColor);
  printBoldAt(171, 286, state, stateColor, 1);
'''
new = '''  // Keep the state right-aligned so long update timestamps can never collide
  // with ONLINE / STALE / OFFLINE. Preserve a 4 px dot-to-label gap.
  gfx->drawFastVLine(158, 280, 20, rgb565(85, 115, 133));
  setText(stateColor, 1);
  int16_t stateX1, stateY1;
  uint16_t stateW, stateH;
  gfx->getTextBounds(state, 0, 0, &stateX1, &stateY1, &stateW, &stateH);
  int stateX = 224 - (int)stateW;
  gfx->fillCircle(stateX - 7, 290, 3, stateColor);
  printBoldAt(stateX, 286, state, stateColor, 1);
'''
assert s.count(old) == 1, 'footer block mismatch'
s = s.replace(old, new)

old = '''  centerBoldText(apparentTitle(), 101, 70, 1, C_WHITE);
'''
new = '''  // Keep the title clear of the right metric stack.
  centerBoldText(apparentTitle(), 94, 70, 1, C_WHITE);
'''
assert s.count(old) == 1, 'hero title mismatch'
s = s.replace(old, new)

old = '''  // Bottom cards use short labels and centered values so adjacent cards do not
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

  drawForecastHighLowCard();
'''
new = '''  // Bottom row: wider wind/direction cards and one secondary line per card.
  // The previous four-line wind card was the main source of visual collisions.
  drawConceptCard(10, 210, 68, 52, 8, true);
  centerBoldText("WIND", 44, 214, 1, rgb565(157, 200, 228));
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 44, 228, 2, C_WHITE);
  centerBoldText("MPH", 44, 243, 1, muted);
  String gustSummary = String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--");
  centerBoldText(gustSummary, 44, 252, 1, rgb565(166, 209, 234));

  drawConceptCard(82, 210, 68, 52, 8, true);
  centerBoldText("DIR", 116, 214, 1, rgb565(157, 200, 228));
  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg));
    setText(C_WHITE, 2);
    int16_t x1, y1;
    uint16_t dirW, dirH;
    gfx->getTextBounds(dirNumber, 0, 0, &x1, &y1, &dirW, &dirH);
    int dirX = 116 - ((int)dirW + 7) / 2;
    printBoldAt(dirX, 229, dirNumber, C_WHITE, 2);
    gfx->drawCircle(dirX + (int)dirW + 3, 231, 2, C_WHITE);
  } else {
    centerBoldText("--", 116, 229, 2, C_WHITE);
  }
  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--",
                 116, 248, 1, rgb565(157, 200, 228));

  drawForecastHighLowCard();
'''
assert s.count(old) == 1, 'bottom row block mismatch'
s = s.replace(old, new)

p.write_text(s)
print('Waveshare 2.8 lower layout retuned')
