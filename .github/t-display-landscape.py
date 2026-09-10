from pathlib import Path

path = Path('T-Display-S3/src/display_ui.cpp')
text = path.read_text()
start_marker = 'static void drawDetailMetricCard'
end_marker = 'void displayBegin()'
start = text.index(start_marker)
end = text.index(end_marker, start)

block = r'''static void drawLandscapeMetricCard(int x, int y, int w, int h,
                                    const String &label, const String &value) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 7, false);

  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font0);
  display.setTextSize(w <= 52 ? 0.54f : 0.62f);
  drawBoldText(label, x + w / 2, y + 11, cyan);
  display.setTextSize(1.0f);

  if (w <= 52 || value.length() > 8) {
    display.setFont(&fonts::Font2);
  } else {
    display.setFont(&fonts::Font4);
  }
  drawBoldText(value, x + w / 2, y + 32, C_WHITE);
}

void drawForecastHighLowCard() {
  if (waitingScreenActive || !detailsPageActive || !wx.valid) return;

  const bool tomorrow = forecastShowsTomorrow();
  String highText = "--";
  String lowText = "--";
  if (wx.forecastValid) {
    const float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    const float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high)) highText = String((int)lroundf(high)) + String("\xB0");
    if (isfinite(low)) lowText = String((int)lroundf(low)) + String("\xB0");
  }

  drawLandscapeMetricCard(215, 79, 49, 51,
                          tomorrow ? "TMRW HIGH" : "TODAY HIGH", highText);
  drawLandscapeMetricCard(267, 79, 49, 51,
                          tomorrow ? "TMRW LOW" : "TODAY LOW", lowText);
}

void drawHeader() {
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 20) station = station.substring(0, 20);

  drawConceptCard(4, 4, 312, 22, 6, true);
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font2);
  drawBoldText(station, 10, 15, C_WHITE);

  display.setTextDatum(textdatum_t::middle_right);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.68f);
  display.setTextColor(rgb565(219, 231, 238));
  display.drawString(currentDateText(), 310, 15);
  display.setTextSize(1.0f);
}

static void drawLandscapeStatusBar(const char *buttonHint) {
  const uint16_t muted = rgb565(168, 198, 216);
  const uint16_t green = rgb565(117, 237, 79);
  const uint16_t red = rgb565(255, 122, 103);
  const uint16_t border = rgb565(23, 78, 108);

  display.fillRect(0, 134, 320, 36, C_BLACK);
  display.drawFastHLine(4, 135, 312, border);

  String left;
  String state;
  uint16_t stateColor = green;

  if (WiFi.status() != WL_CONNECTED) {
    if (setupApStarted) {
      left = "Setup 192.168.4.1";
      state = "SETUP";
    } else {
      left = "Wi-Fi disconnected";
      state = "OFFLINE";
    }
    stateColor = red;
  } else if (!apiConfigured()) {
    left = "Open /config";
    state = "OFFLINE";
    stateColor = red;
  } else if (!wx.valid) {
    left = lastApiError.length() ? "Weather API error" : "Fetching weather...";
    state = "OFFLINE";
    stateColor = red;
  } else {
    left = "Updated " + updateClockText();
    const bool stale = dataStale();
    state = stale ? "STALE" : "ONLINE";
    stateColor = stale ? red : green;
  }

  drawClockIcon(12, 148, muted);
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.68f);
  display.setTextColor(C_WHITE);
  display.drawString(left, 23, 148);

  display.setTextDatum(textdatum_t::middle_right);
  display.fillCircle(267, 148, 2, stateColor);
  drawBoldText(state, 312, 148, stateColor);

  display.setTextDatum(textdatum_t::middle_center);
  display.setTextSize(0.58f);
  display.setTextColor(muted);
  display.drawString(buttonHint, 160, 163);
  display.setTextSize(1.0f);
}

void drawFooter() {
  if (!waitingScreenActive && wx.valid) {
    drawLandscapeStatusBar(detailsPageActive
      ? "EITHER BUTTON: HEAT INDEX"
      : "EITHER BUTTON: DETAILS");
    return;
  }
  drawLandscapeStatusBar("");
}

void drawWaitingScreen() {
  waitingScreenActive = true;
  display.fillScreen(C_BLACK);
  drawHeader();

  drawConceptCard(8, 32, 304, 96, 11, true);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font4);
  display.setTextSize(1.0f);
  display.setTextColor(C_WHITE);
  display.drawString(setupApStarted ? "SETUP" : "WAITING", 160, 59);

  display.setFont(&fonts::Font2);
  display.setTextColor(rgb565(159, 183, 201));
  if (setupApStarted) {
    display.drawString("Connect to setup Wi-Fi", 160, 88);
    display.setFont(&fonts::Font0);
    display.setTextSize(0.82f);
    display.setTextColor(rgb565(114, 202, 255));
    display.drawString(setupApName(), 160, 109);
  } else {
    display.drawString(lastApiError.length() ? "Weather API error" : "Preparing display", 160, 84);
    display.setFont(&fonts::Font0);
    display.setTextSize(0.82f);
    display.setTextColor(rgb565(114, 202, 255));
    if (WiFi.status() != WL_CONNECTED) {
      display.drawString("Connecting to Wi-Fi...", 160, 107);
    } else if (!apiConfigured()) {
      display.drawString("API setup needed", 160, 107);
    } else if (lastApiError.length()) {
      display.drawString("Check provider configuration", 160, 107);
    } else {
      display.drawString("Fetching weather...", 160, 107);
    }
  }
  display.setTextSize(1.0f);
  drawFooter();
}

static void drawLandscapeApparentValue(float apparentF) {
  const String value = String((int)lroundf(apparentF));
  const float scale = value.length() >= 3 ? 1.0f : 1.12f;

  display.setTextColor(C_WHITE);
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font7);
  display.setTextSize(scale);
  const int valueWidth = display.textWidth(value);

  display.setFont(&fonts::Font4);
  display.setTextSize(1.0f);
  const int fWidth = display.textWidth("F");
  const int groupWidth = valueWidth + 17 + fWidth;
  const int startX = 54 + (126 - groupWidth) / 2;

  display.setFont(&fonts::Font7);
  display.setTextSize(scale);
  display.drawString(value, startX, 90);

  const int degreeX = startX + valueWidth + 3;
  display.drawCircle(degreeX + 2, 71, 3, C_WHITE);
  display.setFont(&fonts::Font4);
  display.setTextSize(1.0f);
  display.drawString("F", degreeX + 9, 92);
}

static void drawFullScreenHero() {
  const float apparentF = apparentOutdoorF();
  const RiskStyle risk = riskFor(apparentF);
  const bool cold = windChillApplies();

  for (int y = 0; y < 170; ++y) {
    const float t = (float)y / 169.0f;
    display.drawFastHLine(0, y, 320, lerp565(risk.panelTop, risk.panelBottom, t));
  }

  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 19) station = station.substring(0, 19);
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font2);
  drawBoldText(station, 9, 14, C_WHITE);

  display.setTextDatum(textdatum_t::middle_right);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.68f);
  display.setTextColor(rgb565(235, 242, 247));
  display.drawString(currentDateText(), 311, 14);
  display.setTextSize(1.0f);
  display.drawFastHLine(8, 27, 304, risk.accent);

  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentTitle(), 117, 43, C_WHITE);

  if (cold) drawHeroWind(14, 78);
  else drawHeroSun(25, 88);
  drawLandscapeApparentValue(apparentF);

  display.setFont(&fonts::Font0);
  display.setTextSize(0.62f);
  display.setTextColor(rgb565(235, 242, 247));
  display.drawString("CURRENT RISK", 246, 43);
  display.setTextSize(1.0f);

  display.fillRoundRect(188, 53, 116, 31, 15, risk.status);
  display.drawRoundRect(188, 53, 116, 31, 15, risk.accent);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentRiskLabel(), 246, 69, risk.accent);

  display.setFont(&fonts::Font0);
  display.setTextSize(0.66f);
  display.setTextColor(rgb565(235, 242, 247));
  display.drawString(cold ? "APPARENT COLD" : "APPARENT HEAT", 246, 98);
  display.setTextSize(0.58f);
  display.drawString("LIVE STATION CONDITIONS", 246, 113);
  display.setTextSize(1.0f);

  drawLandscapeStatusBar("EITHER BUTTON: DETAILS");
}

static void drawDetailsScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  const String temp = isfinite(wx.tempF)
    ? String(wx.tempF, 1) + String("\xB0") + "F" : "--";
  const String humidity = isfinite(wx.humidity)
    ? String((int)lroundf(wx.humidity)) + "%" : "--";
  const String dew = isfinite(wx.dewPointF)
    ? String(wx.dewPointF, 1) + String("\xB0") + "F" : "--";
  const String delta = signedTempDelta(wx.fromYesterdayF);

  String wind = isfinite(wx.windMph) ? String(wx.windMph, 1) : "--";
  wind += " / ";
  wind += isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--";

  String direction = "--";
  if (isfinite(wx.windDirDeg)) {
    direction = directionText(wx.windDirDeg) + " " +
      String((int)lroundf(wx.windDirDeg)) + String("\xB0");
  }

  drawLandscapeMetricCard(4, 28, 75, 48, "TEMPERATURE", temp);
  drawLandscapeMetricCard(82, 28, 75, 48, "HUMIDITY", humidity);
  drawLandscapeMetricCard(160, 28, 75, 48, "DEW POINT", dew);
  drawLandscapeMetricCard(238, 28, 78, 48, "VS YDAY", delta);

  drawLandscapeMetricCard(4, 79, 117, 51, "WIND / GUST MPH", wind);
  drawLandscapeMetricCard(124, 79, 88, 51, "DIRECTION", direction);
  drawForecastHighLowCard();

  drawLandscapeStatusBar("EITHER BUTTON: HEAT INDEX");
}

void drawWeatherScreen() {
  if (!wx.valid) {
    drawWaitingScreen();
    return;
  }

  waitingScreenActive = false;
  if (detailsPageActive) drawDetailsScreen();
  else drawFullScreenHero();
}

void toggleDisplayPage() {
  if (!wx.valid || waitingScreenActive) return;
  detailsPageActive = !detailsPageActive;
  Serial.printf("T-Display page: %s\n", detailsPageActive ? "details" : "heat-index");
  drawWeatherScreen();
}

bool displayDetailPageActive() {
  return detailsPageActive;
}

'''

text = text[:start] + block + text[end:]
old_rotation = '  display.setRotation(0);'
assert old_rotation in text, 'expected portrait rotation not found'
text = text.replace(old_rotation, '  display.setRotation(1);', 1)
path.write_text(text)
