#include <WiFi.h>
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

  // Ask for an uncompressed JSON body. More importantly, read the complete
  // response through HTTPClient before handing it to ArduinoJson. Parsing
  // getStream() directly is fragile when the upstream response uses chunked
  // transfer encoding and can surface as ArduinoJson InvalidInput on HTTP 200.
  http.addHeader("Accept", "application/json");
  http.addHeader("Accept-Encoding", "identity");

  Serial.printf("Forecast request: lat=%.5f lon=%.5f\n", wx.latitude, wx.longitude);

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

  String body = http.getString();
  http.end();
  body.trim();
  if (!body.length()) {
    errorOut = "Forecast returned an empty response body";
    return false;
  }

  DynamicJsonDocument doc(4096);
  DeserializationError jsonErr = deserializeJson(doc, body);
  if (jsonErr) {
    String preview = body;
    preview.replace("\r", " ");
    preview.replace("\n", " ");
    if (preview.length() > 120) preview = preview.substring(0, 120);
    errorOut = "Forecast JSON error: " + String(jsonErr.c_str());
    if (preview.length()) {
      errorOut += " body=";
      errorOut += preview;
    }
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

  // A coordinate change may trigger an immediate forecast attempt, but a
  // failed first attempt must still obey FORECAST_RETRY_SECONDS. Previously
  // lastForecastLatitude/Longitude were only stored after success, leaving
  // locationChanged=true forever and causing a retry every second.
  if (lastForecastPollMs != 0) {
    const unsigned long elapsedMs = nowMs - lastForecastPollMs;
    if (!locationChanged && elapsedMs < intervalMs) {
      return wx.forecastValid;
    }
    if (locationChanged && elapsedMs < FORECAST_RETRY_SECONDS * 1000UL) {
      return wx.forecastValid;
    }
  }

  lastForecastPollMs = nowMs;
  lastForecastLatitude = wx.latitude;
  lastForecastLongitude = wx.longitude;

  String error;
  if (!fetchForecastHighLow(error)) {
    lastForecastError = error;
    Serial.println("Forecast poll failed: " + error);
    return false;
  }

  lastForecastError = "";
  if (forceRedraw) drawForecastHighLowCard();
  return true;
}
