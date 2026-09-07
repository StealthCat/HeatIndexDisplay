from pathlib import Path

PROJECTS = [
    Path('T-Display-S3'),
    Path('Waveshare-ESP32-S3-Touch-LCD-2.8'),
]


def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly 1 match in {path}, found {count}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')


def append_after_once(path: Path, marker: str, addition: str, label: str):
    text = path.read_text(encoding='utf-8')
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly 1 marker in {path}, found {count}')
    path.write_text(text.replace(marker, marker + addition, 1), encoding='utf-8')


FORECAST_H = '''#pragma once
#include <Arduino.h>

bool fetchForecastHighLow(String &errorOut);
bool pollForecastIfDue(bool forceRedraw);
bool forecastShowsTomorrow();
'''

FORECAST_CPP = r'''#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <math.h>
#include "app_state.h"
#include "forecast_weather.h"
#include "display_ui.h"
#include "config.h"

static float lastForecastLatitude = NAN;
static float lastForecastLongitude = NAN;

bool forecastShowsTomorrow() {
  if (!wx.forecastValid ||
      !isfinite(wx.forecastTomorrowHighF) ||
      !isfinite(wx.forecastTomorrowLowF)) {
    return false;
  }
  const unsigned long periodMs = FORECAST_CARD_SWITCH_SECONDS * 1000UL;
  return periodMs > 0 && ((millis() / periodMs) & 1UL) != 0;
}

bool fetchForecastHighLow(String &errorOut) {
  errorOut = "";

  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!wx.valid || !isfinite(wx.latitude) || !isfinite(wx.longitude)) {
    errorOut = "Weather station coordinates are not available";
    return false;
  }

  String url = String(OPEN_METEO_FORECAST_URL);
  url += "?latitude=";
  url += String(wx.latitude, 6);
  url += "&longitude=";
  url += String(wx.longitude, 6);
  url += "&daily=temperature_2m_max,temperature_2m_min";
  url += "&temperature_unit=fahrenheit";
  url += "&timezone=auto";
  url += "&forecast_days=2";

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(12);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(15000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.9");

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize forecast HTTPS request";
    return false;
  }

  int code = http.GET();
  lastForecastHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Forecast HTTP " + String(code);
    if (body.length()) {
      errorOut += ": ";
      errorOut += body;
    }
    http.end();
    return false;
  }

  DynamicJsonDocument doc(4096);
  DeserializationError jsonErr = deserializeJson(doc, http.getStream());
  http.end();

  if (jsonErr) {
    errorOut = "Forecast JSON error: " + String(jsonErr.c_str());
    return false;
  }

  JsonArray highs = doc["daily"]["temperature_2m_max"].as<JsonArray>();
  JsonArray lows = doc["daily"]["temperature_2m_min"].as<JsonArray>();
  if (highs.isNull() || lows.isNull() || highs.size() < 2 || lows.size() < 2) {
    errorOut = "Forecast response did not contain today and tomorrow high/low";
    return false;
  }

  float todayHigh = highs[0].as<float>();
  float todayLow = lows[0].as<float>();
  float tomorrowHigh = highs[1].as<float>();
  float tomorrowLow = lows[1].as<float>();

  if (!isfinite(todayHigh) || !isfinite(todayLow) ||
      !isfinite(tomorrowHigh) || !isfinite(tomorrowLow)) {
    errorOut = "Forecast returned invalid temperature values";
    return false;
  }

  wx.forecastTodayHighF = todayHigh;
  wx.forecastTodayLowF = todayLow;
  wx.forecastTomorrowHighF = tomorrowHigh;
  wx.forecastTomorrowLowF = tomorrowLow;
  wx.forecastFetchedMs = millis();
  wx.forecastValid = true;

  Serial.printf(
    "Forecast: today=%.1f/%.1fF tomorrow=%.1f/%.1fF lat=%.5f lon=%.5f\n",
    wx.forecastTodayHighF, wx.forecastTodayLowF,
    wx.forecastTomorrowHighF, wx.forecastTomorrowLowF,
    wx.latitude, wx.longitude
  );
  return true;
}

bool pollForecastIfDue(bool forceRedraw) {
  if (!wx.valid || !isfinite(wx.latitude) || !isfinite(wx.longitude)) {
    return false;
  }

  const unsigned long nowMs = millis();
  const bool locationChanged =
    !isfinite(lastForecastLatitude) ||
    !isfinite(lastForecastLongitude) ||
    fabsf(wx.latitude - lastForecastLatitude) > 0.0001f ||
    fabsf(wx.longitude - lastForecastLongitude) > 0.0001f;

  const unsigned long intervalSeconds = wx.forecastValid
                                      ? FORECAST_REFRESH_SECONDS
                                      : FORECAST_RETRY_SECONDS;
  const unsigned long intervalMs = intervalSeconds * 1000UL;

  if (!locationChanged && lastForecastPollMs != 0 &&
      nowMs - lastForecastPollMs < intervalMs) {
    return wx.forecastValid;
  }

  lastForecastPollMs = nowMs;
  String error;
  if (!fetchForecastHighLow(error)) {
    lastForecastError = error;
    Serial.println("Forecast poll failed: " + error);
    return false;
  }

  lastForecastError = "";
  lastForecastLatitude = wx.latitude;
  lastForecastLongitude = wx.longitude;

  if (forceRedraw) {
    drawForecastHighLowCard();
  }
  return true;
}
'''

for project in PROJECTS:
    # New forecast module.
    (project / 'include' / 'forecast_weather.h').write_text(FORECAST_H, encoding='utf-8')
    (project / 'src' / 'forecast_weather.cpp').write_text(FORECAST_CPP, encoding='utf-8')

    # Shared state additions.
    app_state_h = project / 'include' / 'app_state.h'
    replace_once(
        app_state_h,
        '  float windDirDeg = NAN;\n  float yesterdayTempF = NAN;\n',
        '  float windDirDeg = NAN;\n'
        '  float latitude = NAN;\n'
        '  float longitude = NAN;\n'
        '  float yesterdayTempF = NAN;\n',
        'add station coordinates',
    )
    replace_once(
        app_state_h,
        '  float todayHighF = NAN;\n  float todayLowF = NAN;\n  uint64_t dateUtcMs = 0;\n',
        '  float todayHighF = NAN;\n'
        '  float todayLowF = NAN;\n'
        '  float forecastTodayHighF = NAN;\n'
        '  float forecastTodayLowF = NAN;\n'
        '  float forecastTomorrowHighF = NAN;\n'
        '  float forecastTomorrowLowF = NAN;\n'
        '  uint64_t dateUtcMs = 0;\n',
        'add forecast values',
    )
    replace_once(
        app_state_h,
        '  unsigned long summaryFetchedMs = 0;\n  bool summaryValid = false;\n  bool valid = false;\n',
        '  unsigned long summaryFetchedMs = 0;\n'
        '  unsigned long forecastFetchedMs = 0;\n'
        '  bool summaryValid = false;\n'
        '  bool forecastValid = false;\n'
        '  bool valid = false;\n',
        'add forecast state',
    )
    append_after_once(
        app_state_h,
        'extern String lastSummaryError;\n',
        'extern unsigned long lastForecastPollMs;\n'
        'extern String lastForecastError;\n'
        'extern int lastForecastHttpCode;\n',
        'add forecast globals',
    )

    app_state_cpp = project / 'src' / 'app_state.cpp'
    append_after_once(
        app_state_cpp,
        'String lastSummaryError;\n',
        'unsigned long lastForecastPollMs = 0;\n'
        'String lastForecastError;\n'
        'int lastForecastHttpCode = 0;\n',
        'define forecast globals',
    )

    # Configuration constants.
    config_h = project / 'include' / 'config.h'
    append_after_once(
        config_h,
        '#define WUNDERGROUND_DAILY_HISTORY_URL "https://api.weather.com/v2/pws/history/daily"\n',
        '#define OPEN_METEO_FORECAST_URL    "https://api.open-meteo.com/v1/forecast"\n'
        '#define FORECAST_REFRESH_SECONDS  900UL\n'
        '#define FORECAST_RETRY_SECONDS    60UL\n'
        '#define FORECAST_CARD_SWITCH_SECONDS 30UL\n',
        'add forecast config',
    )

    # Public display API.
    display_h = project / 'include' / 'display_ui.h'
    append_after_once(
        display_h,
        'void drawFooter();\n',
        'void drawForecastHighLowCard();\n',
        'add forecast card declaration',
    )

    # Capture station coordinates from each configured current-observation source.
    ambient_cpp = project / 'src' / 'ambient_weather.cpp'
    replace_once(
        ambient_cpp,
        '  wx.windDirDeg = tryField(last, "winddir");\n  wx.dateUtcMs = last["dateutc"] | 0ULL;\n',
        '  wx.windDirDeg = tryField(last, "winddir");\n\n'
        '  JsonObject coordValues = selected["info"]["coords"]["coords"].as<JsonObject>();\n'
        '  float stationLat = coordValues.isNull() ? NAN : tryField(coordValues, "lat");\n'
        '  float stationLon = coordValues.isNull() ? NAN : tryField(coordValues, "lon");\n'
        '  if ((!isfinite(stationLat) || !isfinite(stationLon))) {\n'
        '    JsonArray geo = selected["info"]["coords"]["geo"]["coordinates"].as<JsonArray>();\n'
        '    if (!geo.isNull() && geo.size() >= 2) {\n'
        '      stationLon = geo[0].as<float>();\n'
        '      stationLat = geo[1].as<float>();\n'
        '    }\n'
        '  }\n'
        '  if (isfinite(stationLat) && isfinite(stationLon)) {\n'
        '    wx.latitude = stationLat;\n'
        '    wx.longitude = stationLon;\n'
        '  }\n\n'
        '  wx.dateUtcMs = last["dateutc"] | 0ULL;\n',
        'capture Ambient coordinates',
    )
    # Version string for requests/logging consistency.
    text = ambient_cpp.read_text(encoding='utf-8').replace('/7.8.1', '/7.9')
    ambient_cpp.write_text(text, encoding='utf-8')

    wu_cpp = project / 'src' / 'wunderground_weather.cpp'
    replace_once(
        wu_cpp,
        '  wx.windDirDeg = wuFloat(obs["winddir"]);\n\n  uint64_t epoch = obs["epoch"] | 0ULL;\n',
        '  wx.windDirDeg = wuFloat(obs["winddir"]);\n'
        '  wx.latitude = wuFloat(obs["lat"]);\n'
        '  wx.longitude = wuFloat(obs["lon"]);\n\n'
        '  uint64_t epoch = obs["epoch"] | 0ULL;\n',
        'capture WU coordinates',
    )
    text = wu_cpp.read_text(encoding='utf-8').replace('/7.8.1', '/7.9').replace('/7.8', '/7.9')
    wu_cpp.write_text(text, encoding='utf-8')

    # Forecast polling and 30-second Today/Tomorrow card alternation.
    controller = project / 'src' / 'app_controller.cpp'
    replace_once(
        controller,
        '#include "display_ui.h"\n',
        '#include "display_ui.h"\n#include "forecast_weather.h"\n',
        'include forecast controller',
    )
    replace_once(
        controller,
        '  pollWeatherSource(true);\n}\n\nvoid appLoop() {\n',
        '  pollWeatherSource(true);\n'
        '  pollForecastIfDue(true);\n'
        '}\n\n'
        'void appLoop() {\n'
        '  static bool forecastPhaseInitialized = false;\n'
        '  static bool lastForecastTomorrow = false;\n',
        'startup forecast poll',
    )
    replace_once(
        controller,
        '  if (nowMs - lastUiStateCheckMs >= 1000UL) {\n'
        '    lastUiStateCheckMs = nowMs;\n'
        '    String newKey = footerStateKey();\n',
        '  if (nowMs - lastUiStateCheckMs >= 1000UL) {\n'
        '    lastUiStateCheckMs = nowMs;\n\n'
        '    if (WiFi.status() == WL_CONNECTED && wx.valid) {\n'
        '      pollForecastIfDue(true);\n'
        '    }\n\n'
        '    if (wx.forecastValid) {\n'
        '      bool showTomorrow = forecastShowsTomorrow();\n'
        '      if (!forecastPhaseInitialized || showTomorrow != lastForecastTomorrow) {\n'
        '        lastForecastTomorrow = showTomorrow;\n'
        '        forecastPhaseInitialized = true;\n'
        '        drawForecastHighLowCard();\n'
        '      }\n'
        '    } else {\n'
        '      forecastPhaseInitialized = false;\n'
        '    }\n\n'
        '    String newKey = footerStateKey();\n',
        '30 second forecast card switching',
    )

# Board-specific display implementations.

tdisplay = Path('T-Display-S3/src/display_ui.cpp')
replace_once(
    tdisplay,
    '#include "display_ui.h"\n',
    '#include "display_ui.h"\n#include "forecast_weather.h"\n',
    'T display forecast include',
)
append_after_once(
    tdisplay,
    'String signedTempDelta(float value) {\n'
    '  if (!isfinite(value)) return "--";\n'
    '  String s;\n'
    '  if (value >= 0.0f) s += "+";\n'
    '  s += String(value, 1);\n'
    '  s += "F";\n'
    '  return s;\n'
    '}\n',
    r'''

void drawForecastHighLowCard() {
  const uint16_t cyan = rgb565(65, 205, 255);
  const uint16_t yellow = rgb565(255, 195, 25);
  const uint16_t cardBg = rgb565(2, 25, 43);
  const bool tomorrow = forecastShowsTomorrow();

  drawMetricCard(7, 258, 156, 29);
  drawSunIcon(20, 272, yellow);
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, cardBg);

  String hl = "-- / --";
  if (wx.forecastValid) {
    float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high) && isfinite(low)) {
      hl = String(high, 1) + " / " + String(low, 1) + "F";
    }
  }
  display.drawString(hl, 37, 267);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, cardBg);
  display.drawString(tomorrow ? "Tomorrow High / Low" : "Today's High / Low", 37, 281);
}
''',
    'T display forecast card function',
)
replace_once(
    tdisplay,
    '  // Today\'s high / low card\n'
    '  drawMetricCard(7, 258, 156, 29);\n'
    '  drawSunIcon(20, 272, yellow);\n'
    '  display.setFont(&fonts::Font2);\n'
    '  display.setTextColor(C_WHITE, rgb565(2, 25, 43));\n'
    '  String hl = "-- / --";\n'
    '  if (wx.summaryValid) {\n'
    '    hl = String(wx.todayHighF, 1) + " / " + String(wx.todayLowF, 1) + "F";\n'
    '  }\n'
    '  display.drawString(hl, 37, 267);\n'
    '  display.setFont(&fonts::Font0);\n'
    '  display.setTextColor(cyan, rgb565(2, 25, 43));\n'
    '  display.drawString("Today\'s High / Low", 37, 281);\n',
    '  // Forecast high / low card alternates Today and Tomorrow every 30 seconds.\n'
    '  drawForecastHighLowCard();\n',
    'replace T display history high-low card',
)

waveshare = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
replace_once(
    waveshare,
    '#include "display_ui.h"\n',
    '#include "display_ui.h"\n#include "forecast_weather.h"\n',
    'Waveshare forecast include',
)
append_after_once(
    waveshare,
    'String signedTempDelta(float value) {\n'
    '  if (!isfinite(value)) return "--";\n'
    '  String s;\n'
    '  if (value >= 0.0f) s += "+";\n'
    '  s += String(value, 1);\n'
    '  s += "F";\n'
    '  return s;\n'
    '}\n',
    r'''

void drawForecastHighLowCard() {
  const uint16_t cyan = rgb565(65, 205, 255);
  const uint16_t yellow = rgb565(255, 195, 25);
  const bool tomorrow = forecastShowsTomorrow();

  drawRoundedRectCard(143, 201, 87, 68);
  drawSunIcon(158, 228, yellow);
  setText(C_WHITE, 1);
  gfx->setCursor(174, 211);

  if (wx.forecastValid) {
    float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high) && isfinite(low)) {
      gfx->print(String(high, 1));
      gfx->print(" / ");
      gfx->print(String(low, 1));
      gfx->print("F");
    } else {
      gfx->print("-- / --");
    }
  } else {
    gfx->print("-- / --");
  }

  setText(cyan, 1);
  gfx->setCursor(174, 231);
  gfx->print(tomorrow ? "Tomorrow" : "Today's");
  gfx->setCursor(174, 244);
  gfx->print("High / Low");
}
''',
    'Waveshare forecast card function',
)
replace_once(
    waveshare,
    '  // Today\'s High / Low is aligned to the right-side metric column above:\n'
    '  // same x position and width as Temperature/Humidity/Dew Point/Yesterday.\n'
    '  drawRoundedRectCard(143, 201, 87, 68);\n'
    '  drawSunIcon(158, 228, yellow);\n'
    '  setText(C_WHITE, 1);\n'
    '  gfx->setCursor(174, 211);\n'
    '  if (wx.summaryValid) {\n'
    '    gfx->print(String(wx.todayHighF, 1));\n'
    '    gfx->print(" / ");\n'
    '    gfx->print(String(wx.todayLowF, 1));\n'
    '    gfx->print("F");\n'
    '  } else {\n'
    '    gfx->print("-- / --");\n'
    '  }\n'
    '  setText(cyan, 1);\n'
    '  gfx->setCursor(174, 231);\n'
    '  gfx->print("Today\'s");\n'
    '  gfx->setCursor(174, 244);\n'
    '  gfx->print("High / Low");\n',
    '  // Forecast High / Low keeps the approved geometry and alternates\n'
    '  // Today and Tomorrow every 30 seconds.\n'
    '  drawForecastHighLowCard();\n',
    'replace Waveshare history high-low card',
)

# Web UI: expose forecast data and make it clear the selected PWS source still
# supplies current conditions / From Yesterday while the card uses forecast REST.
for project in PROJECTS:
    web = project / 'src' / 'web_ui.cpp'
    replace_once(
        web,
        '    if (wx.summaryValid) {\n'
        '      html += F("Today\'s high / low: <b>");\n'
        '      html += String(wx.todayHighF, 1);\n'
        '      html += F("&deg;F / ");\n'
        '      html += String(wx.todayLowF, 1);\n'
        '      html += F("&deg;F</b><br>");\n'
        '    }\n',
        '    if (wx.forecastValid) {\n'
        '      html += F("Forecast today high / low: <b>");\n'
        '      html += String(wx.forecastTodayHighF, 1);\n'
        '      html += F("&deg;F / ");\n'
        '      html += String(wx.forecastTodayLowF, 1);\n'
        '      html += F("&deg;F</b><br>");\n'
        '      html += F("Forecast tomorrow high / low: <b>");\n'
        '      html += String(wx.forecastTomorrowHighF, 1);\n'
        '      html += F("&deg;F / ");\n'
        '      html += String(wx.forecastTomorrowLowF, 1);\n'
        '      html += F("&deg;F</b><br>");\n'
        '    }\n',
        'web forecast values',
    )
    replace_once(
        web,
        '  html += F("<p class=\'muted\'>The selected source is used for current conditions and its REST history API supplies From Yesterday and Today\'s High / Low.</p></div>");\n',
        '  html += F("<p class=\'muted\'>The selected source is used for current conditions and its REST history API supplies From Yesterday. Forecast High / Low uses the station coordinates with the Open-Meteo forecast REST API.</p></div>");\n',
        'web source description',
    )
    replace_once(
        web,
        '    if (wx.summaryValid) {\n'
        '      s += ",\\\"today_high_f\\\":" + String(wx.todayHighF, 2);\n'
        '      s += ",\\\"today_low_f\\\":" + String(wx.todayLowF, 2);\n'
        '    }\n'
        '    s += ",\\\"observation_age_seconds\\\":" + String(observationAgeSeconds());\n',
        '    if (wx.summaryValid) {\n'
        '      s += ",\\\"observed_today_high_f\\\":" + String(wx.todayHighF, 2);\n'
        '      s += ",\\\"observed_today_low_f\\\":" + String(wx.todayLowF, 2);\n'
        '    }\n'
        '    if (wx.forecastValid) {\n'
        '      s += ",\\\"forecast_today_high_f\\\":" + String(wx.forecastTodayHighF, 2);\n'
        '      s += ",\\\"forecast_today_low_f\\\":" + String(wx.forecastTodayLowF, 2);\n'
        '      s += ",\\\"forecast_tomorrow_high_f\\\":" + String(wx.forecastTomorrowHighF, 2);\n'
        '      s += ",\\\"forecast_tomorrow_low_f\\\":" + String(wx.forecastTomorrowLowF, 2);\n'
        '    }\n'
        '    s += ",\\\"observation_age_seconds\\\":" + String(observationAgeSeconds());\n',
        'JSON forecast values',
    )
    replace_once(
        web,
        '  if (lastApiError.length()) {\n',
        '  if (lastForecastHttpCode) {\n'
        '    html += F("<tr><th>Forecast HTTP code</th><td>");\n'
        '    html += String(lastForecastHttpCode);\n'
        '    html += F("</td></tr>");\n'
        '  }\n'
        '  if (lastForecastError.length()) {\n'
        '    html += F("<tr><th>Forecast warning</th><td class=\'bad\'>");\n'
        '    html += htmlEscape(lastForecastError);\n'
        '    html += F("</td></tr>");\n'
        '  }\n\n'
        '  if (lastApiError.length()) {\n',
        'web forecast status rows',
    )

# Architecture and release documentation.
arch = Path('ARCHITECTURE.md')
replace_once(
    arch,
    '| `wunderground_weather.*` | Weather Underground PWS current/history polling and JSON parsing |\n',
    '| `wunderground_weather.*` | Weather Underground PWS current/history polling and JSON parsing |\n'
    '| `forecast_weather.*` | Two-day forecast high/low retrieval and 30-second Today/Tomorrow card phase |\n',
    'architecture forecast module',
)

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')
text = text.replace('## Current release: V7.8.1\n\nV7.8.1 keeps the approved production layouts and provider selection while making live provider summaries more reliable. Ambient widens its same-time-yesterday REST window. Weather Underground now prefers recent 7-day hourly REST observations for Today High/Low and From Yesterday, then falls back to recent 1-day and archived history products.\n',
'''## Current release: V7.9\n\nV7.9 changes the High / Low card to forecast temperatures. The firmware uses the selected station's coordinates with Open-Meteo's two-day daily forecast REST API, shows today's forecast high/low for 30 seconds, then tomorrow's forecast high/low for 30 seconds, repeating continuously. From Yesterday remains sourced from the configured Ambient Weather or Weather Underground history REST API.\n''')
text += '''\n\n## Production Release V7.9\n\nThe High / Low card now uses forecast data rather than observed daily extrema. Both weather-source modes obtain station coordinates from their current-observation payload, then request a two-day daily forecast from Open-Meteo. The card alternates Today's and Tomorrow's forecast high/low every 30 seconds without changing the approved card geometry. Forecast data refreshes every 15 minutes, with a 60-second retry interval until the first successful forecast. See `RELEASE_V7_9_FORECAST_HIGH_LOW.md`.\n'''
readme.write_text(text, encoding='utf-8')

Path('RELEASE_V7_9_FORECAST_HIGH_LOW.md').write_text('''# Production V7.9 - Forecast High / Low\n\nV7.9 changes the display High / Low card from observed daily extrema to forecast temperatures.\n\n- Ambient Weather and Weather Underground continue to supply current observations.\n- From Yesterday continues to come from the configured provider's history REST API.\n- The current provider payload supplies the station latitude/longitude.\n- Forecast High / Low is requested from `https://api.open-meteo.com/v1/forecast` with `temperature_2m_max`, `temperature_2m_min`, Fahrenheit units, `timezone=auto`, and a two-day forecast window.\n- The card displays Today's forecast High / Low for 30 seconds, then Tomorrow's forecast High / Low for 30 seconds, repeating continuously.\n- Forecast data refreshes every 15 minutes. If no forecast has succeeded yet, failed requests retry every 60 seconds.\n- A forecast failure does not interfere with current conditions or From Yesterday.\n- The web status page and `/status` JSON expose forecast values and errors.\n\nOpen-Meteo is used as the common forecast source because Ambient Weather's documented REST API is for past/present station data, while Weather Company forecast endpoints may require separate forecast entitlements beyond a PWS observation API key.\n''', encoding='utf-8')

print('V7.9 forecast patch applied successfully.')
