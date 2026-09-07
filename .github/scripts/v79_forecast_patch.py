from pathlib import Path

PROJECTS = [Path('T-Display-S3'), Path('Waveshare-ESP32-S3-Touch-LCD-2.8')]


def rep(path, old, new, label):
    text = path.read_text(encoding='utf-8')
    if old not in text:
        if new in text:
            print(f'{label}: already applied')
            return
        raise RuntimeError(f'{label}: marker not found in {path}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'{label}: applied')


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
    !isfinite(lastForecastLatitude) || !isfinite(lastForecastLongitude) ||
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
  if (forceRedraw) drawForecastHighLowCard();
  return true;
}
'''

for project in PROJECTS:
    (project / 'include' / 'forecast_weather.h').write_text(FORECAST_H, encoding='utf-8')
    (project / 'src' / 'forecast_weather.cpp').write_text(FORECAST_CPP, encoding='utf-8')

    p = project / 'include' / 'app_state.h'
    rep(p,
        '  float windDirDeg = NAN;\n  float yesterdayTempF = NAN;\n',
        '  float windDirDeg = NAN;\n  float latitude = NAN;\n  float longitude = NAN;\n  float yesterdayTempF = NAN;\n',
        f'{project}: coordinates')
    rep(p,
        '  float todayHighF = NAN;\n  float todayLowF = NAN;\n  uint64_t dateUtcMs = 0;\n',
        '  float todayHighF = NAN;\n  float todayLowF = NAN;\n  float forecastTodayHighF = NAN;\n  float forecastTodayLowF = NAN;\n  float forecastTomorrowHighF = NAN;\n  float forecastTomorrowLowF = NAN;\n  uint64_t dateUtcMs = 0;\n',
        f'{project}: forecast fields')
    rep(p,
        '  unsigned long summaryFetchedMs = 0;\n  bool summaryValid = false;\n  bool valid = false;\n',
        '  unsigned long summaryFetchedMs = 0;\n  unsigned long forecastFetchedMs = 0;\n  bool summaryValid = false;\n  bool forecastValid = false;\n  bool valid = false;\n',
        f'{project}: forecast state')
    rep(p,
        'extern String lastSummaryError;\n',
        'extern String lastSummaryError;\nextern unsigned long lastForecastPollMs;\nextern String lastForecastError;\nextern int lastForecastHttpCode;\n',
        f'{project}: forecast globals')

    p = project / 'src' / 'app_state.cpp'
    rep(p,
        'String lastSummaryError;\n',
        'String lastSummaryError;\nunsigned long lastForecastPollMs = 0;\nString lastForecastError;\nint lastForecastHttpCode = 0;\n',
        f'{project}: forecast global definitions')

    p = project / 'include' / 'config.h'
    rep(p,
        '#define WUNDERGROUND_DAILY_HISTORY_URL "https://api.weather.com/v2/pws/history/daily"\n',
        '#define WUNDERGROUND_DAILY_HISTORY_URL "https://api.weather.com/v2/pws/history/daily"\n#define OPEN_METEO_FORECAST_URL    "https://api.open-meteo.com/v1/forecast"\n#define FORECAST_REFRESH_SECONDS  900UL\n#define FORECAST_RETRY_SECONDS    60UL\n#define FORECAST_CARD_SWITCH_SECONDS 30UL\n',
        f'{project}: forecast constants')

    p = project / 'include' / 'display_ui.h'
    rep(p,
        'void drawFooter();\n',
        'void drawFooter();\nvoid drawForecastHighLowCard();\n',
        f'{project}: display forecast API')

    p = project / 'src' / 'ambient_weather.cpp'
    rep(p,
        '  wx.windDirDeg = tryField(last, "winddir");\n  wx.dateUtcMs = last["dateutc"] | 0ULL;\n',
        '''  wx.windDirDeg = tryField(last, "winddir");

  JsonObject coordValues = selected["info"]["coords"]["coords"].as<JsonObject>();
  float stationLat = coordValues.isNull() ? NAN : tryField(coordValues, "lat");
  float stationLon = coordValues.isNull() ? NAN : tryField(coordValues, "lon");
  if (!isfinite(stationLat) || !isfinite(stationLon)) {
    JsonArray geo = selected["info"]["coords"]["geo"]["coordinates"].as<JsonArray>();
    if (!geo.isNull() && geo.size() >= 2) {
      stationLon = geo[0].as<float>();
      stationLat = geo[1].as<float>();
    }
  }
  if (isfinite(stationLat) && isfinite(stationLon)) {
    wx.latitude = stationLat;
    wx.longitude = stationLon;
  }

  wx.dateUtcMs = last["dateutc"] | 0ULL;
''',
        f'{project}: Ambient coordinates')
    text = p.read_text(encoding='utf-8').replace('/7.8.1', '/7.9')
    p.write_text(text, encoding='utf-8')

    p = project / 'src' / 'wunderground_weather.cpp'
    rep(p,
        '  wx.windDirDeg = wuFloat(obs["winddir"]);\n\n  uint64_t epoch = obs["epoch"] | 0ULL;\n',
        '  wx.windDirDeg = wuFloat(obs["winddir"]);\n  wx.latitude = wuFloat(obs["lat"]);\n  wx.longitude = wuFloat(obs["lon"]);\n\n  uint64_t epoch = obs["epoch"] | 0ULL;\n',
        f'{project}: WU coordinates')
    text = p.read_text(encoding='utf-8').replace('/7.8.1', '/7.9').replace('/7.8', '/7.9')
    p.write_text(text, encoding='utf-8')

    p = project / 'src' / 'app_controller.cpp'
    rep(p,
        '#include "display_ui.h"\n',
        '#include "display_ui.h"\n#include "forecast_weather.h"\n',
        f'{project}: controller include')
    rep(p,
        '  pollWeatherSource(true);\n}\n\nvoid appLoop() {\n',
        '  pollWeatherSource(true);\n  pollForecastIfDue(true);\n}\n\nvoid appLoop() {\n  static bool forecastPhaseInitialized = false;\n  static bool lastForecastTomorrow = false;\n',
        f'{project}: startup forecast')
    rep(p,
        '  if (nowMs - lastUiStateCheckMs >= 1000UL) {\n    lastUiStateCheckMs = nowMs;\n    String newKey = footerStateKey();\n',
        '''  if (nowMs - lastUiStateCheckMs >= 1000UL) {
    lastUiStateCheckMs = nowMs;

    if (WiFi.status() == WL_CONNECTED && wx.valid) {
      pollForecastIfDue(true);
    }

    if (wx.forecastValid) {
      bool showTomorrow = forecastShowsTomorrow();
      if (!forecastPhaseInitialized || showTomorrow != lastForecastTomorrow) {
        lastForecastTomorrow = showTomorrow;
        forecastPhaseInitialized = true;
        drawForecastHighLowCard();
      }
    } else {
      forecastPhaseInitialized = false;
    }

    String newKey = footerStateKey();
''',
        f'{project}: 30-second alternation')

# T-Display card.
p = Path('T-Display-S3/src/display_ui.cpp')
rep(p, '#include "display_ui.h"\n', '#include "display_ui.h"\n#include "forecast_weather.h"\n', 'T display include')
rep(p,
    'String signedTempDelta(float value) {\n  if (!isfinite(value)) return "--";\n  String s;\n  if (value >= 0.0f) s += "+";\n  s += String(value, 1);\n  s += "F";\n  return s;\n}\n',
    '''String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s;
  if (value >= 0.0f) s += "+";
  s += String(value, 1);
  s += "F";
  return s;
}

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
    'T display forecast card function')
rep(p,
    '''  // Today's high / low card
  drawMetricCard(7, 258, 156, 29);
  drawSunIcon(20, 272, yellow);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, rgb565(2, 25, 43));
  String hl = "-- / --";
  if (wx.summaryValid) {
    hl = String(wx.todayHighF, 1) + " / " + String(wx.todayLowF, 1) + "F";
  }
  display.drawString(hl, 37, 267);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, rgb565(2, 25, 43));
  display.drawString("Today's High / Low", 37, 281);
''',
    '''  // Forecast high / low card alternates Today and Tomorrow every 30 seconds.
  drawForecastHighLowCard();
''',
    'T display replace card')

# Waveshare card.
p = Path('Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp')
rep(p, '#include "display_ui.h"\n', '#include "display_ui.h"\n#include "forecast_weather.h"\n', 'Waveshare include')
rep(p,
    'String signedTempDelta(float value) {\n  if (!isfinite(value)) return "--";\n  String s;\n  if (value >= 0.0f) s += "+";\n  s += String(value, 1);\n  s += "F";\n  return s;\n}\n',
    '''String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s;
  if (value >= 0.0f) s += "+";
  s += String(value, 1);
  s += "F";
  return s;
}

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
    'Waveshare forecast card function')
rep(p,
    '''  // Today's High / Low is aligned to the right-side metric column above:
  // same x position and width as Temperature/Humidity/Dew Point/Yesterday.
  drawRoundedRectCard(143, 201, 87, 68);
  drawSunIcon(158, 228, yellow);
  setText(C_WHITE, 1);
  gfx->setCursor(174, 211);
  if (wx.summaryValid) {
    gfx->print(String(wx.todayHighF, 1));
    gfx->print(" / ");
    gfx->print(String(wx.todayLowF, 1));
    gfx->print("F");
  } else {
    gfx->print("-- / --");
  }
  setText(cyan, 1);
  gfx->setCursor(174, 231);
  gfx->print("Today's");
  gfx->setCursor(174, 244);
  gfx->print("High / Low");
''',
    '''  // Forecast High / Low keeps the approved geometry and alternates Today/Tomorrow.
  drawForecastHighLowCard();
''',
    'Waveshare replace card')

# Documentation only after the functional patch has succeeded.
arch = Path('ARCHITECTURE.md')
text = arch.read_text(encoding='utf-8')
needle = '| `wunderground_weather.*` | Weather Underground PWS current/history polling and JSON parsing |\n'
if '| `forecast_weather.*` |' not in text:
    if needle not in text:
        raise RuntimeError('architecture marker not found')
    text = text.replace(needle, needle + '| `forecast_weather.*` | Two-day forecast high/low retrieval and 30-second Today/Tomorrow card phase |\n', 1)
arch.write_text(text, encoding='utf-8')

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')
old = '## Current release: V7.8.1\n\nV7.8.1 keeps the approved production layouts and provider selection while making live provider summaries more reliable. Ambient widens its same-time-yesterday REST window. Weather Underground now prefers recent 7-day hourly REST observations for Today High/Low and From Yesterday, then falls back to recent 1-day and archived history products.\n'
new = '## Current release: V7.9\n\nV7.9 changes the High / Low card to forecast temperatures. The selected station coordinates are used with Open-Meteo\'s two-day daily forecast REST API. The card shows today\'s forecast high/low for 30 seconds, then tomorrow\'s for 30 seconds, repeating continuously. From Yesterday remains sourced from the configured Ambient Weather or Weather Underground history REST API.\n'
if old in text:
    text = text.replace(old, new, 1)
elif '## Current release: V7.9' not in text:
    raise RuntimeError('README release marker not found')
if '## Production Release V7.9' not in text:
    text += '\n\n## Production Release V7.9\n\nThe High / Low card now uses forecast data rather than observed daily extrema. Both weather-source modes obtain station coordinates from their current-observation payload, then request a two-day daily forecast from Open-Meteo. The card alternates Today and Tomorrow every 30 seconds without changing the approved card geometry. Forecast data refreshes every 15 minutes, with a 60-second retry until the first successful forecast. See `RELEASE_V7_9_FORECAST_HIGH_LOW.md`.\n'
readme.write_text(text, encoding='utf-8')

Path('RELEASE_V7_9_FORECAST_HIGH_LOW.md').write_text('''# Production V7.9 - Forecast High / Low

V7.9 changes the display High / Low card from observed daily extrema to forecast temperatures.

- Ambient Weather and Weather Underground continue to supply current observations.
- From Yesterday continues to come from the configured provider history REST API.
- The current provider payload supplies station latitude/longitude.
- Forecast High / Low uses Open-Meteo `temperature_2m_max` and `temperature_2m_min` in Fahrenheit with `timezone=auto` and a two-day forecast window.
- The card displays Today for 30 seconds, then Tomorrow for 30 seconds, repeating continuously.
- Forecast data refreshes every 15 minutes, with a 60-second retry until the first success.
- Forecast failures do not interfere with current observations or From Yesterday.

Open-Meteo is the common forecast source because Ambient Weather's documented REST API exposes past/present station data rather than forecast data, while Weather Company forecast products may require separate forecast entitlements beyond a PWS observation key.
''', encoding='utf-8')

print('V7.9 forecast patch applied successfully')
