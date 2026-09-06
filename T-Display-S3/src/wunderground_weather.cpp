#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <time.h>
#include <math.h>
#include "app_state.h"
#include "wunderground_weather.h"
#include "config_store.h"
#include "display_ui.h"
#include "ui_state.h"
#include "weather_math.h"
#include "config.h"

static unsigned long lastWundergroundRequestMs = 0;

static String wuUrlEncode(const String &s) {
  static const char hex[] = "0123456789ABCDEF";
  String out;
  out.reserve(s.length() * 3);
  for (size_t i = 0; i < s.length(); i++) {
    uint8_t c = (uint8_t)s[i];
    if ((c >= 'a' && c <= 'z') ||
        (c >= 'A' && c <= 'Z') ||
        (c >= '0' && c <= '9') ||
        c == '-' || c == '_' || c == '.' || c == '~') {
      out += (char)c;
    } else {
      out += '%';
      out += hex[c >> 4];
      out += hex[c & 0x0F];
    }
  }
  return out;
}

static float wuFloat(JsonVariantConst value) {
  return value.isNull() ? NAN : value.as<float>();
}

static void respectWundergroundRateLimit() {
  if (lastWundergroundRequestMs == 0) return;
  unsigned long elapsed = millis() - lastWundergroundRequestMs;
  if (elapsed >= 1100UL) return;

  unsigned long waitMs = 1100UL - elapsed;
  while (waitMs > 0) {
    unsigned long slice = waitMs > 50UL ? 50UL : waitMs;
    delay(slice);
    if (webStarted) server.handleClient();
    waitMs -= slice;
  }
}

static String localDateYmd(uint64_t utcMs) {
  if (utcMs == 0) return "";
  time_t t = (time_t)(utcMs / 1000ULL);
  struct tm localTm;
  localtime_r(&t, &localTm);
  char buf[9];
  strftime(buf, sizeof(buf), "%Y%m%d", &localTm);
  return String(buf);
}

static bool fetchHistoryDate(const String &dateYmd, DynamicJsonDocument &doc, String &errorOut) {
  errorOut = "";
  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!weatherUndergroundConfigured()) {
    errorOut = "Weather Underground API key/station ID are not configured";
    return false;
  }
  if (!dateYmd.length()) {
    errorOut = "Unable to determine history date";
    return false;
  }

  String url = String(WUNDERGROUND_HISTORY_URL)
             + "?stationId=" + wuUrlEncode(cfg.wuStationId)
             + "&format=json&units=e&date=" + dateYmd
             + "&numericPrecision=decimal&apiKey=" + wuUrlEncode(cfg.wuApiKey);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(12);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(15000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.7");

  respectWundergroundRateLimit();

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize Weather Underground history request";
    return false;
  }

  int code = http.GET();
  lastWundergroundRequestMs = millis();
  lastSummaryHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Weather Underground history HTTP " + String(code);
    if (body.length()) {
      errorOut += ": ";
      errorOut += body;
    }
    http.end();
    return false;
  }

  StaticJsonDocument<256> filter;
  filter["observations"][0]["epoch"] = true;
  filter["observations"][0]["imperial"]["temp"] = true;
  filter["observations"][0]["imperial"]["windGust"] = true;

  DeserializationError jsonErr = deserializeJson(
    doc,
    http.getStream(),
    DeserializationOption::Filter(filter)
  );
  http.end();

  if (jsonErr) {
    errorOut = "Weather Underground history JSON error: " + String(jsonErr.c_str());
    return false;
  }

  JsonArray observations = doc["observations"].as<JsonArray>();
  if (observations.isNull() || observations.size() == 0) {
    errorOut = "Weather Underground history returned no observations for " + dateYmd;
    return false;
  }
  return true;
}

bool fetchWeatherUndergroundCurrent(String &errorOut) {
  errorOut = "";
  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!weatherUndergroundConfigured()) {
    errorOut = "Weather Underground API key and station ID are not configured";
    return false;
  }

  String url = String(WUNDERGROUND_CURRENT_URL)
             + "?stationId=" + wuUrlEncode(cfg.wuStationId)
             + "&format=json&units=e&numericPrecision=decimal&apiKey="
             + wuUrlEncode(cfg.wuApiKey);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(10);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(12000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.7");

  respectWundergroundRateLimit();

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize Weather Underground HTTPS request";
    return false;
  }

  int code = http.GET();
  lastWundergroundRequestMs = millis();
  lastHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Weather Underground HTTP " + String(code);
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
    errorOut = "Weather Underground JSON error: " + String(jsonErr.c_str());
    return false;
  }

  JsonArray observations = doc["observations"].as<JsonArray>();
  if (observations.isNull() || observations.size() == 0) {
    errorOut = "Weather Underground returned no current observation";
    return false;
  }

  JsonObject obs = observations[0].as<JsonObject>();
  JsonObject imperial = obs["imperial"].as<JsonObject>();
  if (imperial.isNull()) {
    errorOut = "Weather Underground response is missing imperial measurements";
    return false;
  }

  float temp = wuFloat(imperial["temp"]);
  float humidity = wuFloat(obs["humidity"]);
  if (!isfinite(temp) || !isfinite(humidity) || humidity < 0.0f || humidity > 100.0f) {
    errorOut = "Weather Underground returned invalid temperature/humidity";
    return false;
  }

  wx.tempF = temp;
  wx.humidity = humidity;
  wx.heatIndexF = nwsHeatIndexF(wx.tempF, wx.humidity);
  wx.dewPointF = wuFloat(imperial["dewpt"]);
  if (!isfinite(wx.dewPointF)) wx.dewPointF = dewPointFromTempHumidityF(wx.tempF, wx.humidity);
  wx.windMph = wuFloat(imperial["windSpeed"]);
  wx.gustMph = wuFloat(imperial["windGust"]);
  if (!isfinite(wx.maxDailyGustMph) && isfinite(wx.gustMph)) wx.maxDailyGustMph = wx.gustMph;
  wx.windChillF = nwsWindChillF(wx.tempF, wx.windMph);
  wx.windDirDeg = wuFloat(obs["winddir"]);

  uint64_t epoch = obs["epoch"] | 0ULL;
  wx.dateUtcMs = epoch * 1000ULL;
  wx.fetchedMs = millis();
  wx.valid = true;

  String foundName = String((const char*)(obs["neighborhood"] | ""));
  foundName.trim();
  if (!foundName.length()) foundName = String((const char*)(obs["stationID"] | ""));
  if (!foundName.length()) foundName = cfg.wuStationId;
  if (foundName != cfg.stationName) {
    cfg.stationName = foundName;
    saveConfig();
  }

  return true;
}

bool fetchWeatherUndergroundSummary(String &errorOut) {
  errorOut = "";
  if (!wx.valid || wx.dateUtcMs == 0) {
    errorOut = "Current observation is not available";
    return false;
  }

  const uint64_t targetYesterdayMs =
      wx.dateUtcMs > 86400000ULL ? wx.dateUtcMs - 86400000ULL : 0ULL;

  String todayYmd = localDateYmd(wx.dateUtcMs);
  String yesterdayYmd = localDateYmd(targetYesterdayMs);

  DynamicJsonDocument todayDoc(32768);
  String todayError;
  if (!fetchHistoryDate(todayYmd, todayDoc, todayError)) {
    errorOut = todayError;
    return false;
  }

  float high = wx.tempF;
  float low = wx.tempF;
  float maxGust = isfinite(wx.gustMph) ? wx.gustMph : NAN;

  for (JsonObject point : todayDoc["observations"].as<JsonArray>()) {
    JsonObject imperial = point["imperial"].as<JsonObject>();
    float pointTemp = wuFloat(imperial["temp"]);
    float pointGust = wuFloat(imperial["windGust"]);

    if (isfinite(pointTemp)) {
      if (!isfinite(high) || pointTemp > high) high = pointTemp;
      if (!isfinite(low) || pointTemp < low) low = pointTemp;
    }
    if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) {
      maxGust = pointGust;
    }
  }

  todayDoc.clear();

  DynamicJsonDocument yesterdayDoc(32768);
  String yesterdayError;
  if (!fetchHistoryDate(yesterdayYmd, yesterdayDoc, yesterdayError)) {
    errorOut = yesterdayError;
    return false;
  }

  float yesterday = NAN;
  uint64_t bestDifference = UINT64_MAX;

  for (JsonObject point : yesterdayDoc["observations"].as<JsonArray>()) {
    uint64_t epoch = point["epoch"] | 0ULL;
    JsonObject imperial = point["imperial"].as<JsonObject>();
    float pointTemp = wuFloat(imperial["temp"]);
    if (epoch == 0 || !isfinite(pointTemp)) continue;

    uint64_t pointMs = epoch * 1000ULL;
    uint64_t delta = pointMs > targetYesterdayMs
                   ? pointMs - targetYesterdayMs
                   : targetYesterdayMs - pointMs;
    if (delta < bestDifference) {
      bestDifference = delta;
      yesterday = pointTemp;
    }
  }

  wx.todayHighF = high;
  wx.todayLowF = low;
  wx.maxDailyGustMph = maxGust;
  wx.yesterdayTempF = yesterday;
  wx.fromYesterdayF = isfinite(yesterday) ? wx.tempF - yesterday : NAN;
  wx.summaryValid = isfinite(wx.todayHighF) && isfinite(wx.todayLowF);
  wx.summaryFetchedMs = millis();
  return true;
}

bool pollWeatherUnderground(bool forceRedraw) {
  WeatherData before = wx;
  String stationNameBefore = cfg.stationName;

  String error;
  if (!fetchWeatherUndergroundCurrent(error)) {
    lastApiError = error;
    Serial.println("Weather Underground poll failed: " + error);
    if (forceRedraw) {
      lastFooterStateKey = "";
      drawFooter();
    }
    return false;
  }

  lastApiError = "";
  lastPollMs = millis();

  const unsigned long SUMMARY_REFRESH_MS = 300000UL;
  if (lastSummaryPollMs == 0 || millis() - lastSummaryPollMs >= SUMMARY_REFRESH_MS) {
    String summaryError;
    if (fetchWeatherUndergroundSummary(summaryError)) {
      lastSummaryError = "";
    } else {
      lastSummaryError = summaryError;
      Serial.println("Weather Underground summary failed: " + summaryError);
    }
    lastSummaryPollMs = millis();
  }

  Serial.printf(
    "Weather Underground: station=%s temp=%.2fF rh=%.1f%% hi=%.2fF wc=%.2fF dew=%.2fF wind=%.2f gust=%.2f dir=%.1f mode=%s\n",
    cfg.wuStationId.c_str(), wx.tempF, wx.humidity, wx.heatIndexF,
    wx.windChillF, wx.dewPointF, wx.windMph, wx.gustMph,
    wx.windDirDeg, apparentTitle()
  );

  bool changed = weatherDisplayChanged(before, wx) ||
                 stationNameBefore != cfg.stationName;

  if (forceRedraw) {
    if (changed) {
      unsigned long drawStart = millis();
      drawWeatherScreen();
      unsigned long drawMs = millis() - drawStart;
      Serial.printf("Display redraw: %lu ms\n", drawMs);
      lastFooterStateKey = footerStateKey();
    } else {
      String newKey = footerStateKey();
      if (newKey != lastFooterStateKey) {
        lastFooterStateKey = newKey;
        drawFooter();
      }
    }
  }

  return true;
}
