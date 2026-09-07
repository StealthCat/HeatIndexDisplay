from pathlib import Path

PROJECTS = [
    Path('T-Display-S3'),
    Path('Waveshare-ESP32-S3-Touch-LCD-2.8'),
]


def replace_function(text: str, signature: str, replacement: str) -> str:
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    end = None
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise RuntimeError(f'Could not find end of {signature}')
    return text[:start] + replacement.rstrip() + text[end:]


# ---------------------------------------------------------------------------
# T-Display S3
# ---------------------------------------------------------------------------
t_path = PROJECTS[0] / 'src' / 'display_ui.cpp'
t = t_path.read_text()

t_card = r'''void drawMetricCard(int x, int y, int w, int h) {
  const uint16_t bg = rgb565(3, 27, 45);
  const uint16_t border = rgb565(11, 82, 119);
  display.fillRoundRect(x, y, w, h, 7, bg);
  display.drawRoundRect(x, y, w, h, 7, border);
}

static void drawBoldText(const String &text, int x, int y, uint16_t color) {
  display.setTextColor(color);
  display.drawString(text, x, y);
  display.drawString(text, x + 1, y);
}'''
t = replace_function(t, 'void drawMetricCard(', t_card)

t_forecast = r'''void drawForecastHighLowCard() {
  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t yellow = rgb565(255, 205, 35);
  const bool tomorrow = forecastShowsTomorrow();

  drawMetricCard(7, 258, 156, 29);
  drawSunIcon(20, 272, yellow);

  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font0);
  drawBoldText(tomorrow ? "TOMORROW HIGH / LOW" : "TODAY HIGH / LOW", 37, 264, cyan);

  String hl = "-- / --";
  if (wx.forecastValid) {
    float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high) && isfinite(low)) {
      hl = String(high, 1) + " / " + String(low, 1) + "F";
    }
  }

  display.setFont(&fonts::Font2);
  drawBoldText(hl, 37, 278, C_WHITE);
}'''
t = replace_function(t, 'void drawForecastHighLowCard(', t_forecast)

t_header = r'''void drawHeader() {
  display.setTextDatum(textdatum_t::middle_left);

  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() <= 12) {
    display.setFont(&fonts::Font4);
  } else {
    display.setFont(&fonts::Font2);
    if (station.length() > 18) station = station.substring(0, 18);
  }

  drawBoldText(station, 8, 24, C_WHITE);
  display.drawFastHLine(8, 48, 154, rgb565(45, 205, 235));
}'''
t = replace_function(t, 'void drawHeader(', t_header)

t_weather = r'''void drawWeatherScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t muted = rgb565(165, 190, 205);
  const uint16_t green = rgb565(120, 225, 70);
  const uint16_t cardBg = rgb565(3, 27, 45);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);

  // Main apparent-temperature card.
  display.fillRoundRect(8, 54, 154, 88, 10, risk.panel);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentTitle(), 85, 66, C_WHITE);

  String value = String((int)lroundf(apparentF));
  display.setFont(&fonts::Font7);
  display.setTextColor(C_WHITE);
  display.drawString(value, 73, 96);

  int valueWidth = display.textWidth(value);
  int rightEdge = 73 + valueWidth / 2;
  display.drawCircle(rightEdge + 5, 81, 3, C_WHITE);

  display.setFont(&fonts::Font4);
  display.drawString("F", rightEdge + 17, 103);

  display.fillRoundRect(16, 118, 138, 18, 6, risk.status);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentRiskLabel(), 85, 127, C_WHITE);

  // Compact metric cards use a consistent hierarchy: label first, value below.
  display.setTextDatum(textdatum_t::middle_left);

  // Temperature
  drawMetricCard(7, 147, 77, 34);
  drawThermometer(13, 153, rgb565(255, 70, 55));
  display.setFont(&fonts::Font0);
  drawBoldText("TEMP", 29, 154, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(String(wx.tempF, 1) + "F", 29, 170, C_WHITE);

  // Humidity
  drawMetricCard(87, 147, 76, 34);
  drawDrop(99, 153, rgb565(50, 165, 255));
  display.setFont(&fonts::Font0);
  drawBoldText("HUMIDITY", 113, 154, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(String((int)lroundf(wx.humidity)) + "%", 113, 170, C_WHITE);

  // Dew point
  drawMetricCard(7, 184, 77, 34);
  drawLeafIcon(19, 198, green);
  display.setFont(&fonts::Font0);
  drawBoldText("DEW POINT", 31, 191, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + "F" : "--", 31, 207, C_WHITE);

  // Difference from yesterday
  drawMetricCard(87, 184, 76, 34);
  drawTrendIcon(94, 195, cyan);
  display.setFont(&fonts::Font0);
  drawBoldText("VS YDAY", 113, 191, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(signedTempDelta(wx.fromYesterdayF), 113, 207, C_WHITE);

  // Wind / gust
  drawMetricCard(7, 221, 77, 34);
  drawWindIcon(13, 231, cyan);
  display.setFont(&fonts::Font0);
  drawBoldText("WIND / GUST", 32, 228, cyan);
  String windLine = isfinite(wx.windMph) ? String(wx.windMph, 1) : "--";
  windLine += " / ";
  windLine += isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--";
  display.setFont(&fonts::Font0);
  drawBoldText(windLine + " mph", 32, 245, C_WHITE);

  // Direction
  drawMetricCard(87, 221, 76, 34);
  drawCompassIcon(100, 238, cyan);
  display.setFont(&fonts::Font0);
  drawBoldText("DIRECTION", 115, 228, cyan);
  String degText = isfinite(wx.windDirDeg)
                 ? String((int)lroundf(wx.windDirDeg)) + String("\xB0")
                 : "--";
  String dirLine = degText;
  if (isfinite(wx.windDirDeg)) {
    dirLine += " ";
    dirLine += directionText(wx.windDirDeg);
  }
  display.setFont(&fonts::Font0);
  drawBoldText(dirLine, 115, 245, C_WHITE);

  drawForecastHighLowCard();
  drawFooter();
}'''
t = replace_function(t, 'void drawWeatherScreen(', t_weather)
t_path.write_text(t)


# ---------------------------------------------------------------------------
# Waveshare 2.8
# ---------------------------------------------------------------------------
w_path = PROJECTS[1] / 'src' / 'display_ui.cpp'
w = w_path.read_text()

w_card = r'''void drawRoundedRectCard(int x, int y, int w, int h) {
  const uint16_t bg = rgb565(3, 27, 45);
  const uint16_t border = rgb565(11, 82, 119);
  gfx->fillRoundRect(x, y, w, h, 8, bg);
  gfx->drawRoundRect(x, y, w, h, 8, border);
}

static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {
  setText(color, size);
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
}

static void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  int x = centerX - (int)w / 2;
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
}'''
w = replace_function(w, 'void drawRoundedRectCard(', w_card)

w_forecast = r'''void drawForecastHighLowCard() {
  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t muted = rgb565(165, 190, 205);
  const uint16_t yellow = rgb565(255, 205, 35);
  const bool tomorrow = forecastShowsTomorrow();

  drawRoundedRectCard(143, 201, 87, 68);
  drawSunIcon(157, 236, yellow);

  printBoldAt(174, 207, tomorrow ? "TOMORROW" : "TODAY", cyan, 1);
  printBoldAt(174, 219, "HIGH / LOW", muted, 1);

  String hl = "-- / --";
  if (wx.forecastValid) {
    float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high) && isfinite(low)) {
      hl = String(high, 1) + "/" + String(low, 1) + "F";
    }
  }
  printBoldAt(174, 242, hl, C_WHITE, 1);
}'''
w = replace_function(w, 'void drawForecastHighLowCard(', w_forecast)

w_header = r'''void headerText() {
  const uint16_t cyan = rgb565(78, 215, 255);

  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 16) station = station.substring(0, 16);
  printBoldAt(14, 17, station, C_WHITE, 2);

  setText(cyan, 1);
  String dateStr = currentDateText();
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(dateStr, 0, 0, &x1, &y1, &w, &h);
  gfx->setCursor(226 - w, 20);
  gfx->print(dateStr);

  gfx->drawFastHLine(14, 44, 212, cyan);
}'''
w = replace_function(w, 'void headerText(', w_header)

w_weather = r'''void drawWeatherScreen() {
  gfx->fillScreen(C_BLACK);
  headerText();

  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t cardBg = rgb565(3, 27, 45);
  const uint16_t muted = rgb565(165, 190, 205);
  const uint16_t green = rgb565(120, 225, 70);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);

  // Large apparent-temperature panel.
  gfx->fillRoundRect(10, 65, 128, 128, 12, risk.panel);
  centerBoldText(apparentTitle(), 74, 78, 2, C_WHITE);

  String value = String((int)lroundf(apparentF));
  setText(C_WHITE, 5);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(value, 0, 0, &x1, &y1, &w, &h);
  int valX = 72 - (int)w / 2;
  gfx->setCursor(valX, 105);
  gfx->print(value);
  gfx->drawCircle(valX + w + 5, 106, 3, C_WHITE);

  setText(C_WHITE, 2);
  gfx->setCursor(valX + w + 12, 119);
  gfx->print("F");

  gfx->fillRoundRect(22, 154, 104, 25, 7, risk.status);
  centerBoldText(apparentRiskLabel(), 74, 161, 2, C_WHITE);

  // Right-side cards: label on top, bold value underneath.
  drawRoundedRectCard(143, 65, 87, 29);
  drawThermometer(150, 68, rgb565(255, 70, 55));
  printBoldAt(170, 67, "TEMP", cyan, 1);
  printBoldAt(170, 77, String(wx.tempF, 1) + "F", C_WHITE, 2);

  drawRoundedRectCard(143, 98, 87, 29);
  drawDrop(158, 101, rgb565(50, 165, 255));
  printBoldAt(170, 100, "HUMIDITY", cyan, 1);
  printBoldAt(170, 110, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);

  drawRoundedRectCard(143, 131, 87, 29);
  drawLeaf(157, 145, green);
  printBoldAt(170, 133, "DEW POINT", cyan, 1);
  printBoldAt(170, 143, isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + "F" : "--", C_WHITE, 2);

  drawRoundedRectCard(143, 164, 87, 29);
  drawTrend(149, 170, cyan);
  printBoldAt(170, 166, "FROM YDAY", cyan, 1);
  printBoldAt(170, 176, signedTempDelta(wx.fromYesterdayF), C_WHITE, 2);

  // Bottom cards keep the approved geometry but use a clearer label/value hierarchy.
  drawRoundedRectCard(10, 201, 62, 68);
  drawWindIcon(16, 219, cyan);
  centerBoldText("WIND", 41, 205, 1, cyan);
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 42, 220, 2, C_WHITE);
  centerBoldText("mph", 41, 239, 1, muted);
  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"), 41, 250, 1, cyan);
  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"), 41, 259, 1, cyan);

  drawRoundedRectCard(76, 201, 62, 68);
  drawCompassIcon(92, 230, cyan);
  centerBoldText("DIRECTION", 107, 205, 1, cyan);
  String degText = isfinite(wx.windDirDeg)
                 ? String((int)lroundf(wx.windDirDeg)) + String((char)247)
                 : "--";
  centerBoldText(degText, 108, 221, 2, C_WHITE);
  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--", 107, 247, 1, cyan);

  drawForecastHighLowCard();
  drawFooter();
}'''
w = replace_function(w, 'void drawWeatherScreen(', w_weather)
w_path.write_text(w)


# Release documentation.
release = Path('RELEASE_V7_10_DISPLAY_POLISH.md')
release.write_text('''# V7.10 — Display polish\n\nV7.10 refines both production display targets for readability and visual hierarchy.\n\n- Small navy cards now show the label first and the data underneath.\n- Small-card labels and values use heavier rendering for better legibility.\n- Station headers, apparent-temperature titles, and risk labels are emphasized.\n- Metric-card borders are slightly brighter and more consistent.\n- Wind, direction, and forecast cards use a clearer label/value hierarchy.\n- Existing approved card geometry and the 30-second Today/Tomorrow forecast alternation are preserved.\n''')

readme = Path('README.md')
text = readme.read_text()
if '## V7.10 display polish' not in text:
    text += '''\n\n## V7.10 display polish\n\nThe production UI now uses a stronger visual hierarchy: labels appear above values in the compact metric cards, values and labels are rendered more boldly, and the wind/direction/forecast cards are easier to scan while preserving the existing display geometry.\n'''
    readme.write_text(text)
