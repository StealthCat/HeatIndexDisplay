from pathlib import Path

p = Path('T-Display-S3/src/display_ui.cpp')
s = p.read_text()

old = '''static void drawLandscapeMetricCard(int x, int y, int w, int h,
                                    const String &label, const String &value) {
  const uint16_t cyan = rgb565(132, 211, 255);
  drawConceptCard(x, y, w, h, 6, false);

  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font0);
  display.setTextSize(1.0f);
  drawBoldText(label, x + 7, y + h / 2, cyan);

  display.setTextDatum(textdatum_t::middle_right);
  display.setFont(&fonts::Font2);
  if (display.textWidth(value) > w - 70) {
    display.setFont(&fonts::Font0);
  }
  drawBoldText(value, x + w - 7, y + h / 2, C_WHITE);
}
'''
new = '''enum MetricValueStyle {
  METRIC_PLAIN,
  METRIC_DEGREE_F,
  METRIC_DEGREE_ONLY,
};

static void drawLandscapeMetricCard(int x, int y, int w, int h,
                                    const String &label, const String &value,
                                    MetricValueStyle style = METRIC_PLAIN) {
  const uint16_t cyan = rgb565(132, 211, 255);
  drawConceptCard(x, y, w, h, 6, false);

  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font0);
  display.setTextSize(1.0f);
  drawBoldText(label, x + 7, y + h / 2, cyan);

  const int rightX = x + w - 7;
  const int centerY = y + h / 2;

  if (style == METRIC_PLAIN || value == "--") {
    display.setTextDatum(textdatum_t::middle_right);
    display.setFont(&fonts::Font2);
    if (display.textWidth(value) > w - 70) {
      display.setFont(&fonts::Font0);
    }
    drawBoldText(value, rightX, centerY, C_WHITE);
    return;
  }

  // Draw degree marks geometrically instead of relying on a bitmap-font
  // degree glyph. This keeps temperatures and compass headings consistent on
  // the physical ST7789 panel.
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font2);
  const int valueW = display.textWidth(value);
  const int fW = style == METRIC_DEGREE_F ? display.textWidth("F") : 0;
  const int degreeSpan = 7;
  const int totalW = valueW + degreeSpan + fW;
  const int startX = rightX - totalW;

  drawBoldText(value, startX, centerY, C_WHITE);
  const int degreeCx = startX + valueW + 3;
  display.drawCircle(degreeCx, centerY - 5, 2, C_WHITE);
  if (style == METRIC_DEGREE_F) {
    drawBoldText("F", degreeCx + 4, centerY, C_WHITE);
  }
}
'''
assert old in s, 'metric card block not found'
s = s.replace(old, new, 1)

old = '''    if (isfinite(high)) highText = String((int)lroundf(high)) + String("\\xB0") + "F";
    if (isfinite(low)) lowText = String((int)lroundf(low)) + String("\\xB0") + "F";
  }

  drawLandscapeMetricCard(4, 106, 154, 24,
                          tomorrow ? "TMRW HIGH" : "TODAY HIGH", highText);
  drawLandscapeMetricCard(162, 106, 154, 24,
                          tomorrow ? "TMRW LOW" : "TODAY LOW", lowText);
'''
new = '''    if (isfinite(high)) highText = String((int)lroundf(high));
    if (isfinite(low)) lowText = String((int)lroundf(low));
  }

  drawLandscapeMetricCard(4, 106, 154, 24,
                          tomorrow ? "TMRW HIGH" : "TODAY HIGH", highText,
                          METRIC_DEGREE_F);
  drawLandscapeMetricCard(162, 106, 154, 24,
                          tomorrow ? "TMRW LOW" : "TODAY LOW", lowText,
                          METRIC_DEGREE_F);
'''
assert old in s, 'forecast block not found'
s = s.replace(old, new, 1)

old = '''  const String temp = isfinite(wx.tempF)
    ? String(wx.tempF, 1) + String("\\xB0") + "F" : "--";
  const String humidity = isfinite(wx.humidity)
    ? String((int)lroundf(wx.humidity)) + "%" : "--";
  const String dew = isfinite(wx.dewPointF)
    ? String(wx.dewPointF, 1) + String("\\xB0") + "F" : "--";
  const String delta = signedTempDelta(wx.fromYesterdayF);
'''
new = '''  const String temp = isfinite(wx.tempF) ? String(wx.tempF, 1) : "--";
  const String humidity = isfinite(wx.humidity)
    ? String((int)lroundf(wx.humidity)) + "%" : "--";
  const String dew = isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) : "--";
  String delta = "--";
  if (isfinite(wx.fromYesterdayF)) {
    if (wx.fromYesterdayF >= 0.0f) delta += "+";
    delta += String(wx.fromYesterdayF, 1);
  }
'''
assert old in s, 'details temperature block not found'
s = s.replace(old, new, 1)

old = '''  String direction = "--";
  if (isfinite(wx.windDirDeg)) {
    direction = directionText(wx.windDirDeg) + " " +
      String((int)lroundf(wx.windDirDeg)) + String("\\xB0");
  }

  drawLandscapeMetricCard(4, 28, 154, 24, "TEMP", temp);
  drawLandscapeMetricCard(162, 28, 154, 24, "HUMIDITY", humidity);
  drawLandscapeMetricCard(4, 54, 154, 24, "DEW POINT", dew);
  drawLandscapeMetricCard(162, 54, 154, 24, "VS YDAY", delta);
  drawLandscapeMetricCard(4, 80, 154, 24, "WIND/GUST", wind);
  drawLandscapeMetricCard(162, 80, 154, 24, "DIRECTION", direction);
'''
new = '''  String direction = "--";
  if (isfinite(wx.windDirDeg)) {
    direction = directionText(wx.windDirDeg) + " " +
      String((int)lroundf(wx.windDirDeg));
  }

  drawLandscapeMetricCard(4, 28, 154, 24, "TEMP", temp, METRIC_DEGREE_F);
  drawLandscapeMetricCard(162, 28, 154, 24, "HUMIDITY", humidity);
  drawLandscapeMetricCard(4, 54, 154, 24, "DEW POINT", dew, METRIC_DEGREE_F);
  drawLandscapeMetricCard(162, 54, 154, 24, "VS YDAY", delta, METRIC_DEGREE_F);
  drawLandscapeMetricCard(4, 80, 154, 24, "WIND/GUST", wind);
  drawLandscapeMetricCard(162, 80, 154, 24, "DIRECTION", direction,
                          METRIC_DEGREE_ONLY);
'''
assert old in s, 'details card block not found'
s = s.replace(old, new, 1)

p.write_text(s)
