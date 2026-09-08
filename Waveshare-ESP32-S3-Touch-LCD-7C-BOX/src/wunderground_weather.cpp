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
static String lastWundergroundObsTimeLocal;

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

static String providerYmdFromLocal(const String &localTime) {
  if (localTime.length() < 10) return "";
  String ymd;
  ymd.reserve(8);
  for (size_t i = 0; i < 10; i++) {
    char c = localTime[i];
    if (c >= '0' && c <= '9') ymd += c;
  }
  return ymd.length() == 8 ? ymd : String();
}

static int providerSecondsOfDay(const String &localTime) {
  if (localTime.length() < 16) return -1;
  int separator = localTime.indexOf(' ');
  if (separator < 0) separator = localTime.indexOf('T');
  if (separator < 0 || separator + 5 >= (int)localTime.length()) return -1;

  int hour = localTime.substring(separator + 1, separator + 3).toInt();
  int minute = localTime.substring(separator + 4, separator + 6).toInt();
  int second = 0;
  if (separator + 8 < (int)localTime.length() && localTime[separator + 6] == ':') {
    second = localTime.substring(separator + 7, separator + 9).toInt();
  }
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) return -1;
  return hour * 3600 + minute * 60 + second;
}

static bool providerLeapYear(int year) {
  return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
}

static int providerDaysInMonth(int year, int month) {
  static const uint8_t days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
  if (month < 1 || month > 12) return 0;
  if (month == 2 && providerLeapYear(year)) return 29;
  return days[month - 1];
}

static String providerPreviousYmd(const String &ymd) {
  if (ymd.length() != 8) return "";
  int year = ymd.substring(0, 4).toInt();
  int month = ymd.substring(4, 6).toInt();
  int day = ymd.substring(6, 8).toInt();
  if (year < 1970 || month < 1 || month > 12 || day < 1 || day > providerDaysInMonth(year, month)) return "";
  day--;
  if (day < 1) {
    month--;
    if (month < 1) {
      month = 12;
      year--;
    }
    day = providerDaysInMonth(year, month);
  }
  char buf[9];
  snprintf(buf, sizeof(buf), "%04d%02d%02d", year, month, day);
  return String(buf);
}

static bool providerLocalMatchesYmd(const String &localTime, const String &ymd) {
  return providerYmdFromLocal(localTime) == ymd;
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
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.9");

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
  filter["observations"][0]["obsTimeLocal"] = true;
filter["observations"][0]["epoch"] = true;
  filter["observations"][0]["imperial"]["tempHigh"] = true;
  filter["observations"][0]["imperial"]["tempLow"] = true;
  filter["observations"][0]["imperial"]["tempAvg"] = true;
  filter["observations"][0]["imperial"]["windgustHigh"] = true;

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

static bool fetchDailyHistoryDate(const String &dateYmd,
                              DynamicJsonDocument &doc,
                              String &errorOut) {
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
    errorOut = "Unable to determine daily history date";
    return false;
  }

  String url = String(WUNDERGROUND_DAILY_HISTORY_URL);
  url += "?stationId=";
  url += wuUrlEncode(cfg.wuStationId);
  url += "&format=json&units=e&date=";
  url += dateYmd;
  url += "&numericPrecision=decimal&apiKey=";
  url += wuUrlEncode(cfg.wuApiKey);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(12);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(15000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.9");

  respectWundergroundRateLimit();

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize Weather Underground daily REST request";
    return false;
  }

  int code = http.GET();
  lastWundergroundRequestMs = millis();
  lastSummaryHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Weather Underground daily REST HTTP " + String(code);
    if (body.length()) {
      errorOut += ": ";
      errorOut += body;
    }
    http.end();
    return false;
  }

  StaticJsonDocument<192> filter;
  filter["observations"][0]["imperial"]["tempHigh"] = true;
  filter["observations"][0]["imperial"]["tempLow"] = true;
  filter["observations"][0]["imperial"]["windgustHigh"] = true;

  DeserializationError jsonErr = deserializeJson(
    doc,
    http.getStream(),
    DeserializationOption::Filter(filter)
  );
  http.end();

  if (jsonErr) {
    errorOut = "Weather Underground daily REST JSON error: " + String(jsonErr.c_str());
    return false;
  }

  JsonArray observations = doc["observations"].as<JsonArray>();
  if (observations.isNull() || observations.size() == 0) {
    errorOut = "Weather Underground daily REST returned no observations for " + dateYmd;
    return false;
  }
  return true;
}

static bool summarizeWundergroundAllHistory(const String &dateYmd,
                                             float &high,
                                             float &low,
                                             float &maxGust,
                                             String &errorOut) {
  DynamicJsonDocument allDoc(32768);
  if (!fetchHistoryDate(dateYmd, allDoc, errorOut)) return false;

  for (JsonObject point : allDoc["observations"].as<JsonArray>()) {
    JsonObject imperial = point["imperial"].as<JsonObject>();
    float pointHigh = wuFloat(imperial["tempHigh"]);
    float pointLow = wuFloat(imperial["tempLow"]);
    float pointGust = wuFloat(imperial["windgustHigh"]);

    if (isfinite(pointHigh) && (!isfinite(high) || pointHigh > high)) high = pointHigh;
    if (isfinite(pointLow) && (!isfinite(low) || pointLow < low)) low = pointLow;
    if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) {
      maxGust = pointGust;
    }
  }
  return isfinite(high) && isfinite(low);
}

static bool fetchRecentWunderground(const char *baseUrl,
                                     DynamicJsonDocument &doc,
                                     String &errorOut,
                                     const char *label) {
  errorOut = "";
  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!weatherUndergroundConfigured()) {
    errorOut = "Weather Underground API key/station ID are not configured";
    return false;
  }

  String url = String(baseUrl);
  url += "?stationId=";
  url += wuUrlEncode(cfg.wuStationId);
  url += "&format=json&units=e&numericPrecision=decimal&apiKey=";
  url += wuUrlEncode(cfg.wuApiKey);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(12);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(15000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.9");

  respectWundergroundRateLimit();

  if (!http.begin(client, url)) {
    errorOut = String("Unable to initialize Weather Underground ") + label + " request";
    return false;
  }

  int code = http.GET();
  lastWundergroundRequestMs = millis();
  lastSummaryHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = String("Weather Underground ") + label + " HTTP " + String(code);
    if (body.length()) {
      errorOut += ": ";
      errorOut += body;
    }
    http.end();
    return false;
  }

  StaticJsonDocument<320> filter;
  filter["observations"][0]["obsTimeLocal"] = true;
  filter["observations"][0]["epoch"] = true;
  filter["observations"][0]["imperial"]["tempHigh"] = true;
  filter["observations"][0]["imperial"]["tempLow"] = true;
  filter["observations"][0]["imperial"]["tempAvg"] = true;
  filter["observations"][0]["imperial"]["windgustHigh"] = true;

  DeserializationError jsonErr = deserializeJson(doc, http.getStream(), DeserializationOption::Filter(filter));
  http.end();

  if (jsonErr) {
    errorOut = String("Weather Underground ") + label + " JSON error: " + String(jsonErr.c_str());
    return false;
  }

  JsonArray observations = doc["observations"].as<JsonArray>();
  if (observations.isNull() || observations.size() == 0) {
    errorOut = String("Weather Underground ") + label + " returned no observations";
    return false;
  }
  return true;
}

static bool summarizeRecentWundergroundDay(JsonArray observations,
                                            const String &ymd,
                                            float &high,
                                            float &low,
                                            float &maxGust) {
  bool sawProviderDay = false;
  for (JsonObject point : observations) {
    String localTime = String((const char*)(point["obsTimeLocal"] | ""));
    if (!providerLocalMatchesYmd(localTime, ymd)) continue;

    JsonObject imperial = point["imperial"].as<JsonObject>();
    float pointHigh = wuFloat(imperial["tempHigh"]);
    float pointLow = wuFloat(imperial["tempLow"]);
    float pointAvg = wuFloat(imperial["tempAvg"]);
    float pointGust = wuFloat(imperial["windgustHigh"]);

    if (!isfinite(pointHigh) && isfinite(pointAvg)) pointHigh = pointAvg;
    if (!isfinite(pointLow) && isfinite(pointAvg)) pointLow = pointAvg;

    if (isfinite(pointHigh)) {
      if (!isfinite(high) || pointHigh > high) high = pointHigh;
      sawProviderDay = true;
    }
    if (isfinite(pointLow)) {
      if (!isfinite(low) || pointLow < low) low = pointLow;
      sawProviderDay = true;
    }
    if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) maxGust = pointGust;
  }
  return sawProviderDay && isfinite(high) && isfinite(low);
}

static float nearestRecentWundergroundTemperature(JsonArray observations,
                                                   const String &ymd,
                                                   int targetSeconds) {
  float yesterday = NAN;
  uint32_t bestDifference = UINT32_MAX;

  for (JsonObject point : observations) {
    String localTime = String((const char*)(point["obsTimeLocal"] | ""));
    if (!providerLocalMatchesYmd(localTime, ymd)) continue;

    int pointSeconds = providerSecondsOfDay(localTime);
    if (pointSeconds < 0) continue;

    JsonObject imperial = point["imperial"].as<JsonObject>();
    float pointTemp = wuFloat(imperial["tempAvg"]);
    if (!isfinite(pointTemp)) {
      float pointHigh = wuFloat(imperial["tempHigh"]);
      float pointLow = wuFloat(imperial["tempLow"]);
      if (isfinite(pointHigh) && isfinite(pointLow)) pointTemp = (pointHigh + pointLow) * 0.5f;
      else if (isfinite(pointHigh)) pointTemp = pointHigh;
      else if (isfinite(pointLow)) pointTemp = pointLow;
    }
    if (!isfinite(pointTemp)) continue;

    uint32_t delta = pointSeconds > targetSeconds
                   ? (uint32_t)(pointSeconds - targetSeconds)
                   : (uint32_t)(targetSeconds - pointSeconds);
    if (delta < bestDifference) {
      bestDifference = delta;
      yesterday = pointTemp;
    }
  }
  return yesterday;
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
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.9");

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
  wx.latitude = wuFloat(obs["lat"]);
  wx.longitude = wuFloat(obs["lon"]);

  uint64_t epoch = obs["epoch"] | 0ULL;
  wx.dateUtcMs = epoch * 1000ULL;
  wx.fetchedMs = millis();
  wx.valid = true;
  lastWundergroundObsTimeLocal = String((const char*)(obs["obsTimeLocal"] | ""));
  lastWundergroundObsTimeLocal.trim();

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

  String todayYmd = providerYmdFromLocal(lastWundergroundObsTimeLocal);
  int targetSeconds = providerSecondsOfDay(lastWundergroundObsTimeLocal);

  if (!todayYmd.length()) todayYmd = localDateYmd(wx.dateUtcMs);
  if (targetSeconds < 0) {
    time_t currentSec = (time_t)(wx.dateUtcMs / 1000ULL);
    struct tm localTm;
    localtime_r(&currentSec, &localTm);
    targetSeconds = localTm.tm_hour * 3600 + localTm.tm_min * 60 + localTm.tm_sec;
  }

  String yesterdayYmd = providerPreviousYmd(todayYmd);
  if (!todayYmd.length() || !yesterdayYmd.length() || targetSeconds < 0) {
    errorOut = "Unable to determine Weather Underground provider-local summary time";
    return false;
  }

  float high = wx.tempF;
  float low = wx.tempF;
  float maxGust = isfinite(wx.gustMph) ? wx.gustMph : NAN;
  float yesterday = NAN;
  bool todayOk = false;
  String recentError;

  DynamicJsonDocument recentDoc(49152);
  if (fetchRecentWunderground(WUNDERGROUND_RECENT_7DAY_HOURLY_URL,
                              recentDoc,
                              recentError,
                              "recent 7-day hourly REST")) {
    JsonArray recent = recentDoc["observations"].as<JsonArray>();
    todayOk = summarizeRecentWundergroundDay(recent, todayYmd, high, low, maxGust);
    yesterday = nearestRecentWundergroundTemperature(recent, yesterdayYmd, targetSeconds);
  }

  if (!todayOk) {
    DynamicJsonDocument rapidDoc(49152);
    String rapidError;
    if (fetchRecentWunderground(WUNDERGROUND_RECENT_1DAY_URL,
                                rapidDoc,
                                rapidError,
                                "recent 1-day REST")) {
      todayOk = summarizeRecentWundergroundDay(rapidDoc["observations"].as<JsonArray>(),
                                               todayYmd,
                                               high,
                                               low,
                                               maxGust);
    } else if (!recentError.length()) {
      recentError = rapidError;
    }
  }

  if (!todayOk) {
    DynamicJsonDocument dailyDoc(4096);
    String dailyError;
    bool dailyOk = fetchDailyHistoryDate(todayYmd, dailyDoc, dailyError);
    if (dailyOk) {
      for (JsonObject point : dailyDoc["observations"].as<JsonArray>()) {
        JsonObject imperial = point["imperial"].as<JsonObject>();
        float pointHigh = wuFloat(imperial["tempHigh"]);
        float pointLow = wuFloat(imperial["tempLow"]);
        float pointGust = wuFloat(imperial["windgustHigh"]);
        if (isfinite(pointHigh) && (!isfinite(high) || pointHigh > high)) high = pointHigh;
        if (isfinite(pointLow) && (!isfinite(low) || pointLow < low)) low = pointLow;
        if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) maxGust = pointGust;
      }
      todayOk = isfinite(high) && isfinite(low);
    }

    if (!todayOk) {
      String fallbackError;
      if (!summarizeWundergroundAllHistory(todayYmd, high, low, maxGust, fallbackError)) {
        errorOut = recentError;
        if (errorOut.length() && dailyError.length()) errorOut += "; daily: ";
        errorOut += dailyError;
        if (errorOut.length() && fallbackError.length()) errorOut += "; archived: ";
        errorOut += fallbackError;
        return false;
      }
      todayOk = true;
    }
  }

  wx.todayHighF = high;
  wx.todayLowF = low;
  wx.maxDailyGustMph = maxGust;
  wx.summaryValid = todayOk && isfinite(wx.todayHighF) && isfinite(wx.todayLowF);
  wx.summaryFetchedMs = millis();

  if (!isfinite(yesterday)) {
    DynamicJsonDocument yesterdayDoc(32768);
    String yesterdayError;
    if (!fetchHistoryDate(yesterdayYmd, yesterdayDoc, yesterdayError)) {
      errorOut = yesterdayError;
      return false;
    }

    yesterday = nearestRecentWundergroundTemperature(yesterdayDoc["observations"].as<JsonArray>(),
                                                     yesterdayYmd,
                                                     targetSeconds);

    if (!isfinite(yesterday)) {
      time_t currentSec = (time_t)(wx.dateUtcMs / 1000ULL);
      struct tm yesterdayTm;
      localtime_r(&currentSec, &yesterdayTm);
      yesterdayTm.tm_mday -= 1;
      yesterdayTm.tm_isdst = -1;
      time_t yesterdaySec = mktime(&yesterdayTm);
      uint64_t targetYesterdayMs = yesterdaySec > 0 ? (uint64_t)yesterdaySec * 1000ULL : 0ULL;
      uint64_t bestDifference = UINT64_MAX;

      for (JsonObject point : yesterdayDoc["observations"].as<JsonArray>()) {
        uint64_t epoch = point["epoch"] | 0ULL;
        JsonObject imperial = point["imperial"].as<JsonObject>();
        float pointTemp = wuFloat(imperial["tempAvg"]);
        if (epoch == 0 || !isfinite(pointTemp)) continue;
        uint64_t pointMs = epoch * 1000ULL;
        uint64_t delta = pointMs > targetYesterdayMs ? pointMs - targetYesterdayMs : targetYesterdayMs - pointMs;
        if (delta < bestDifference) {
          bestDifference = delta;
          yesterday = pointTemp;
        }
      }
    }
  }

  if (!isfinite(yesterday)) {
    errorOut = "Weather Underground REST data did not contain yesterday temperature";
    return false;
  }

  wx.yesterdayTempF = yesterday;
  wx.fromYesterdayF = wx.tempF - yesterday;
  wx.summaryFetchedMs = millis();

  Serial.printf(
    "Weather Underground REST summary: high=%.2fF low=%.2fF yesterday=%.2fF delta=%+.2fF\n",
    wx.todayHighF, wx.todayLowF, wx.yesterdayTempF, wx.fromYesterdayF
  );
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
