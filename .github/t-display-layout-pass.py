from pathlib import Path
import re

ui_path = Path('T-Display-S3/src/display_ui.cpp')
text = ui_path.read_text()


def replace(pattern, replacement, name):
    global text
    text, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'{name}: expected one replacement, got {count}')

# Rework metric cards into wide, single-line cards: native Font0 labels and
# native Font2 values.  This avoids tiny/scaled text on the physical ST7789.
replace(
    r'''static void drawLandscapeMetricCard\(int x, int y, int w, int h,\n                                    const String &label, const String &value\) \{.*?\n\}\n\nvoid drawForecastHighLowCard\(\)''',
    '''static void drawLandscapeMetricCard(int x, int y, int w, int h,\n                                    const String &label, const String &value) {\n  const uint16_t cyan = rgb565(132, 211, 255);\n  drawConceptCard(x, y, w, h, 6, false);\n\n  display.setTextDatum(textdatum_t::middle_left);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(1.0f);\n  drawBoldText(label, x + 7, y + h / 2, cyan);\n\n  display.setTextDatum(textdatum_t::middle_right);\n  display.setFont(&fonts::Font2);\n  if (display.textWidth(value) > w - 70) {\n    display.setFont(&fonts::Font0);\n  }\n  drawBoldText(value, x + w - 7, y + h / 2, C_WHITE);\n}\n\nvoid drawForecastHighLowCard()''',
    'metric card')

# Forecast occupies the fourth row of the new 2-column detail grid.
replace(
    r'''void drawForecastHighLowCard\(\) \{.*?\n\}\n\nvoid drawHeader\(\)''',
    '''void drawForecastHighLowCard() {\n  if (waitingScreenActive || !detailsPageActive || !wx.valid) return;\n\n  const bool tomorrow = forecastShowsTomorrow();\n  String highText = "--";\n  String lowText = "--";\n  if (wx.forecastValid) {\n    const float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;\n    const float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;\n    if (isfinite(high)) highText = String((int)lroundf(high)) + String("\\xB0") + "F";\n    if (isfinite(low)) lowText = String((int)lroundf(low)) + String("\\xB0") + "F";\n  }\n\n  drawLandscapeMetricCard(4, 106, 154, 24,\n                          tomorrow ? "TMRW HIGH" : "TODAY HIGH", highText);\n  drawLandscapeMetricCard(162, 106, 154, 24,\n                          tomorrow ? "TMRW LOW" : "TODAY LOW", lowText);\n}\n\nvoid drawHeader()''',
    'forecast cards')

# Keep the station prominent while using compact native Font0 for the short,
# ASCII-only date/time string from time_utils.cpp.
replace(
    r'''void drawHeader\(\) \{.*?\n\}\n\nstatic void drawLandscapeStatusBar''',
    '''void drawHeader() {\n  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";\n  if (station.length() > 16) station = station.substring(0, 16);\n\n  drawConceptCard(4, 4, 312, 22, 6, true);\n  display.setTextDatum(textdatum_t::middle_left);\n  display.setFont(&fonts::Font2);\n  drawBoldText(station, 10, 15, C_WHITE);\n\n  display.setTextDatum(textdatum_t::middle_right);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(1.0f);\n  display.setTextColor(rgb565(231, 241, 247));\n  display.drawString(currentDateText(), 309, 15);\n}\n\nstatic void drawLandscapeStatusBar''',
    'header')

# Replace the cluttered right-side pill/secondary captions with one clean risk
# card containing only HEAT RISK + the current risk label.
replace(
    r'''static void drawFullScreenHero\(\) \{.*?\n\}\n\nstatic void drawDetailsScreen\(\)''',
    '''static void drawFullScreenHero() {\n  const float apparentF = apparentOutdoorF();\n  const RiskStyle risk = riskFor(apparentF);\n  const bool cold = windChillApplies();\n\n  for (int y = 0; y < 170; ++y) {\n    const float t = (float)y / 169.0f;\n    display.drawFastHLine(0, y, 320, lerp565(risk.panelTop, risk.panelBottom, t));\n  }\n\n  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";\n  if (station.length() > 16) station = station.substring(0, 16);\n  display.setTextDatum(textdatum_t::middle_left);\n  display.setFont(&fonts::Font2);\n  drawBoldText(station, 9, 14, C_WHITE);\n\n  display.setTextDatum(textdatum_t::middle_right);\n  display.setFont(&fonts::Font0);\n  display.setTextSize(1.0f);\n  display.setTextColor(rgb565(241, 247, 250));\n  display.drawString(currentDateText(), 310, 14);\n  display.drawFastHLine(8, 27, 304, risk.accent);\n\n  display.drawFastVLine(180, 35, 91, lerp565(risk.accent, C_WHITE, 0.30f));\n\n  display.setTextDatum(textdatum_t::middle_center);\n  display.setFont(&fonts::Font2);\n  drawBoldText(apparentTitle(), 112, 42, C_WHITE);\n\n  if (cold) drawHeroWind(14, 76);\n  else drawHeroSun(24, 84);\n  drawLandscapeApparentValue(apparentF);\n\n  // A single rectangular risk card is cleaner and avoids the crowded pill\n  // plus APPARENT/LIVE captions from the previous layout.\n  display.fillRoundRect(190, 47, 122, 70, 9, risk.status);\n  display.drawRoundRect(190, 47, 122, 70, 9, risk.accent);\n  display.setFont(&fonts::Font2);\n  display.setTextColor(C_WHITE);\n  display.drawString("HEAT RISK", 251, 62);\n  display.drawFastHLine(201, 75, 100, risk.accent);\n  drawBoldText(apparentRiskLabel(), 251, 94, risk.accent);\n\n  drawLandscapeStatusBar("BUTTON: DETAILS");\n}\n\nstatic void drawDetailsScreen()''',
    'hero')

# Two columns x four rows gives each metric enough width for native-size text.
replace(
    r'''static void drawDetailsScreen\(\) \{.*?\n\}\n\nvoid drawWeatherScreen\(\)''',
    '''static void drawDetailsScreen() {\n  display.fillScreen(C_BLACK);\n  drawHeader();\n\n  const String temp = isfinite(wx.tempF)\n    ? String(wx.tempF, 1) + String("\\xB0") + "F" : "--";\n  const String humidity = isfinite(wx.humidity)\n    ? String((int)lroundf(wx.humidity)) + "%" : "--";\n  const String dew = isfinite(wx.dewPointF)\n    ? String(wx.dewPointF, 1) + String("\\xB0") + "F" : "--";\n  const String delta = signedTempDelta(wx.fromYesterdayF);\n\n  String wind = isfinite(wx.windMph) ? String(wx.windMph, 1) : "--";\n  wind += "/";\n  wind += isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--";\n  wind += " mph";\n\n  String direction = "--";\n  if (isfinite(wx.windDirDeg)) {\n    direction = directionText(wx.windDirDeg) + " " +\n      String((int)lroundf(wx.windDirDeg)) + String("\\xB0");\n  }\n\n  drawLandscapeMetricCard(4, 28, 154, 24, "TEMP", temp);\n  drawLandscapeMetricCard(162, 28, 154, 24, "HUMIDITY", humidity);\n  drawLandscapeMetricCard(4, 54, 154, 24, "DEW POINT", dew);\n  drawLandscapeMetricCard(162, 54, 154, 24, "VS YDAY", delta);\n  drawLandscapeMetricCard(4, 80, 154, 24, "WIND/GUST", wind);\n  drawLandscapeMetricCard(162, 80, 154, 24, "DIRECTION", direction);\n  drawForecastHighLowCard();\n\n  drawLandscapeStatusBar("BUTTON: HEAT INDEX");\n}\n\nvoid drawWeatherScreen()''',
    'details')

ui_path.write_text(text)

# Avoid ESP32/newlib strftime extensions (notably %-I and %-d).  Build the
# short strings explicitly so only known ASCII characters reach the display.
time_path = Path('T-Display-S3/src/time_utils.cpp')
time_path.write_text(r'''#include <time.h>
#include "app_state.h"
#include "time_utils.h"

uint32_t observationAgeSeconds() {
  if (!wx.valid) return 0;
  time_t now = time(nullptr);
  if (wx.dateUtcMs > 0 && now > 1700000000) {
    uint64_t nowMs = (uint64_t)now * 1000ULL;
    if (nowMs >= wx.dateUtcMs) {
      uint64_t sec = (nowMs - wx.dateUtcMs) / 1000ULL;
      if (sec > 0xFFFFFFFFULL) return 0xFFFFFFFFUL;
      return (uint32_t)sec;
    }
  }
  return (millis() - wx.fetchedMs) / 1000UL;
}

bool dataStale() {
  if (!wx.valid || wx.fetchedMs == 0) return false;
  return ((millis() - wx.fetchedMs) / 1000UL) > cfg.staleSeconds;
}

String formatClockFromEpoch(time_t t) {
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

String formatDateFromEpoch(time_t t) {
  if (t <= 100000) return "";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  static const char *MONTHS[] = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
  };
  const int month = (timeinfo.tm_mon >= 0 && timeinfo.tm_mon < 12)
    ? timeinfo.tm_mon : 0;
  char buf[16];
  snprintf(buf, sizeof(buf), "%s %d", MONTHS[month], timeinfo.tm_mday);
  return String(buf);
}

time_t wxEpochSeconds() {
  if (wx.dateUtcMs > 0) return (time_t)(wx.dateUtcMs / 1000ULL);
  return time(nullptr);
}

String updateClockText() {
  return formatClockFromEpoch(wxEpochSeconds());
}

String currentDateText() {
  time_t now = time(nullptr);
  if (now <= 100000) now = wxEpochSeconds();
  if (now <= 100000) return "";
  return formatDateFromEpoch(now) + " " + formatClockFromEpoch(now);
}
''')
