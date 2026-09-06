
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <time.h>
#include <math.h>
#include "config.h"
#include "compile_defaults.h"
#include "ui_assets.h"

WebServer server(80);
Preferences prefs;

struct AppConfig {
  String ssid;
  String wifiPassword;
  String applicationKey;
  String apiKey;
  String macAddress;
  String stationName;
  String hostname = DEFAULT_HOSTNAME;
  String timezoneTz = DEFAULT_TIMEZONE_TZ;
  uint32_t pollSeconds = DEFAULT_POLL_SECONDS;
  uint32_t staleSeconds = DEFAULT_STALE_SECONDS;
};

struct WeatherData {
  float tempF = NAN;
  float humidity = NAN;
  float heatIndexF = NAN;
  float dewPointF = NAN;
  float windMph = NAN;
  float gustMph = NAN;
  float maxDailyGustMph = NAN;
  float windChillF = NAN;
  float windDirDeg = NAN;
  float yesterdayTempF = NAN;
  float fromYesterdayF = NAN;
  float todayHighF = NAN;
  float todayLowF = NAN;
  uint64_t dateUtcMs = 0;
  unsigned long fetchedMs = 0;
  unsigned long summaryFetchedMs = 0;
  bool summaryValid = false;
  bool valid = false;
};

AppConfig cfg;
WeatherData wx;

bool webStarted = false;
bool setupApStarted = false;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastPollMs = 0;
unsigned long lastSummaryPollMs = 0;
unsigned long lastAmbientRequestMs = 0;
unsigned long lastUiStateCheckMs = 0;
String lastFooterStateKey;
String lastApiError;
int lastHttpCode = 0;
int lastSummaryHttpCode = 0;
String lastSummaryError;

void drawWaitingScreen();
void drawWeatherScreen();
void drawFooter();

uint32_t observationAgeSeconds();
bool dataStale();
String updateClockText();

bool fetchAmbientSummary(String &errorOut);

static void respectAmbientRateLimit();
static bool weatherDisplayChanged(const WeatherData &before, const WeatherData &after);
String footerStateKey();

void saveConfig();

static float tryField(JsonObject obj, const char* a, const char* b = nullptr, const char* c = nullptr) {
  if (a && !obj[a].isNull()) return obj[a].as<float>();
  if (b && !obj[b].isNull()) return obj[b].as<float>();
  if (c && !obj[c].isNull()) return obj[c].as<float>();
  return NAN;
}

String htmlEscape(const String &in) {
  String out;
  out.reserve(in.length() + 16);
  for (size_t i = 0; i < in.length(); i++) {
    char c = in[i];
    switch (c) {
      case '&': out += F("&amp;"); break;
      case '<': out += F("&lt;"); break;
      case '>': out += F("&gt;"); break;
      case '"': out += F("&quot;"); break;
      case '\'': out += F("&#39;"); break;
      default: out += c; break;
    }
  }
  return out;
}

String urlEncode(const String &s) {
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

String normalizeMac(String mac) {
  mac.trim();
  mac.toUpperCase();
  mac.replace("-", ":");
  return mac;
}

float dewPointFromTempHumidityF(float tF, float rh) {
  if (!isfinite(tF) || !isfinite(rh) || rh <= 0.0f || rh > 100.0f) return NAN;
  float tC = (tF - 32.0f) * 5.0f / 9.0f;
  const float a = 17.625f;
  const float b = 243.04f;
  float gamma = logf(rh / 100.0f) + (a * tC) / (b + tC);
  float dpC = (b * gamma) / (a - gamma);
  return dpC * 9.0f / 5.0f + 32.0f;
}

float nwsHeatIndexF(float t, float rh) {
  float simple = 0.5f * (t + 61.0f + ((t - 68.0f) * 1.2f) + (rh * 0.094f));
  simple = (simple + t) * 0.5f;
  if (simple < 80.0f) return simple;

  float hi =
      -42.379f
      + 2.04901523f * t
      + 10.14333127f * rh
      - 0.22475541f * t * rh
      - 0.00683783f * t * t
      - 0.05481717f * rh * rh
      + 0.00122874f * t * t * rh
      + 0.00085282f * t * rh * rh
      - 0.00000199f * t * t * rh * rh;

  if (rh < 13.0f && t >= 80.0f && t <= 112.0f) {
    float inside = (17.0f - fabsf(t - 95.0f)) / 17.0f;
    if (inside > 0.0f) hi -= ((13.0f - rh) / 4.0f) * sqrtf(inside);
  } else if (rh > 85.0f && t >= 80.0f && t <= 87.0f) {
    hi += ((rh - 85.0f) / 10.0f) * ((87.0f - t) / 5.0f);
  }
  return hi;
}


float nwsWindChillF(float t, float windMph) {
  if (!isfinite(t) || !isfinite(windMph)) return t;
  if (t > 50.0f || windMph <= 3.0f) return t;
  float v16 = powf(windMph, 0.16f);
  return 35.74f + 0.6215f * t - 35.75f * v16 + 0.4275f * t * v16;
}

bool windChillApplies() {
  return wx.valid && isfinite(wx.tempF) && isfinite(wx.windMph) &&
         wx.tempF <= 50.0f && wx.windMph > 3.0f;
}

float apparentOutdoorF() {
  return windChillApplies() ? wx.windChillF : wx.heatIndexF;
}

const char* apparentTitle() {
  return windChillApplies() ? "WIND CHILL" : "HEAT INDEX";
}

const char* riskLabel(float hi) {
  if (hi >= 125.0f) return "EXTREME DANGER";
  if (hi >= 103.0f) return "DANGER";
  if (hi >= 90.0f)  return "EXTREME CAUTION";
  if (hi >= 80.0f)  return "CAUTION";
  return "NORMAL";
}

const char* coldRiskLabel(float wc) {
  if (wc <= -35.0f) return "EXTREME DANGER";
  if (wc <= -20.0f) return "DANGER";
  if (wc <= 0.0f) return "VERY COLD";
  if (wc <= 20.0f) return "COLD";
  return "CHILLY";
}

const char* apparentRiskLabel() {
  return windChillApplies() ? coldRiskLabel(wx.windChillF) : riskLabel(wx.heatIndexF);
}

String directionText(float deg) {
  if (!isfinite(deg)) return "--";
  static const char* dirs[] = {"N","NNE","NE","ENE","E","ESE","SE","SSE",
                               "S","SSW","SW","WSW","W","WNW","NW","NNW"};
  int idx = (int)floorf((deg + 11.25f) / 22.5f) % 16;
  return String(dirs[idx]);
}


void applyCompileTimeDefaults() {
  cfg.ssid = String(COMPILED_WIFI_SSID);
  cfg.wifiPassword = String(COMPILED_WIFI_PASSWORD);
  cfg.applicationKey = String(COMPILED_AMBIENT_APPLICATION_KEY);
  cfg.apiKey = String(COMPILED_AMBIENT_API_KEY);
  cfg.macAddress = normalizeMac(String(COMPILED_AMBIENT_STATION_MAC));
  cfg.stationName = "";

  String compiledHost = String(COMPILED_HOSTNAME);
  compiledHost.trim();
  cfg.hostname = compiledHost.length() ? compiledHost : String(DEFAULT_HOSTNAME);

  String compiledTz = String(COMPILED_TIMEZONE_TZ);
  compiledTz.trim();
  cfg.timezoneTz = compiledTz.length() ? compiledTz : String(DEFAULT_TIMEZONE_TZ);

  uint32_t compiledPoll = (uint32_t)COMPILED_POLL_SECONDS;
  cfg.pollSeconds = compiledPoll ? compiledPoll : DEFAULT_POLL_SECONDS;

  uint32_t compiledStale = (uint32_t)COMPILED_STALE_SECONDS;
  cfg.staleSeconds = compiledStale ? compiledStale : DEFAULT_STALE_SECONDS;

  if (cfg.pollSeconds < MIN_POLL_SECONDS) cfg.pollSeconds = MIN_POLL_SECONDS;
  if (cfg.staleSeconds < MIN_STALE_SECONDS) cfg.staleSeconds = MIN_STALE_SECONDS;
}


void loadConfig() {
  prefs.begin("heatidx", true);

  const bool initialized = prefs.getBool("cfginit", false);

  // Migration support for firmware versions before V7.4. If any legacy
  // setting key exists, preserve that stored configuration instead of
  // overwriting it with newly compiled defaults.
  const bool legacyConfigPresent =
      prefs.isKey("ssid")   ||
      prefs.isKey("wpass")  ||
      prefs.isKey("appkey") ||
      prefs.isKey("apikey") ||
      prefs.isKey("mac")    ||
      prefs.isKey("stname") ||
      prefs.isKey("host")   ||
      prefs.isKey("tz")     ||
      prefs.isKey("poll")   ||
      prefs.isKey("stale");

  if (initialized || legacyConfigPresent) {
    cfg.ssid = prefs.getString("ssid", "");
    cfg.wifiPassword = prefs.getString("wpass", "");
    cfg.applicationKey = prefs.getString("appkey", "");
    cfg.apiKey = prefs.getString("apikey", "");
    cfg.macAddress = prefs.getString("mac", "");
    cfg.stationName = prefs.getString("stname", "");
    cfg.hostname = prefs.getString("host", DEFAULT_HOSTNAME);
    cfg.timezoneTz = prefs.getString("tz", DEFAULT_TIMEZONE_TZ);
    cfg.pollSeconds = prefs.getUInt("poll", DEFAULT_POLL_SECONDS);
    cfg.staleSeconds = prefs.getUInt("stale", DEFAULT_STALE_SECONDS);
    prefs.end();

    if (!cfg.hostname.length()) cfg.hostname = DEFAULT_HOSTNAME;
    if (!cfg.timezoneTz.length()) cfg.timezoneTz = DEFAULT_TIMEZONE_TZ;
    if (cfg.pollSeconds < MIN_POLL_SECONDS) cfg.pollSeconds = MIN_POLL_SECONDS;
    if (cfg.staleSeconds < MIN_STALE_SECONDS) cfg.staleSeconds = MIN_STALE_SECONDS;

    // Mark migrated pre-V7.4 NVS as initialized without changing its values.
    if (!initialized && legacyConfigPresent) {
      saveConfig();
    }
    return;
  }

  prefs.end();

  // Truly blank NVS: seed the compile-time defaults exactly once, then store
  // them persistently. From this point forward the web configuration is the
  // source of truth until Factory Reset clears NVS.
  applyCompileTimeDefaults();
  saveConfig();

  Serial.println("Seeded first-boot configuration from compile_defaults.h");
}


void saveConfig() {
  prefs.begin("heatidx", false);
  prefs.putBool("cfginit", true);
  prefs.putString("ssid", cfg.ssid);
  prefs.putString("wpass", cfg.wifiPassword);
  prefs.putString("appkey", cfg.applicationKey);
  prefs.putString("apikey", cfg.apiKey);
  prefs.putString("mac", cfg.macAddress);
  prefs.putString("stname", cfg.stationName);
  prefs.putString("host", cfg.hostname);
  prefs.putString("tz", cfg.timezoneTz);
  prefs.putUInt("poll", cfg.pollSeconds);
  prefs.putUInt("stale", cfg.staleSeconds);
  prefs.end();
}


bool apiConfigured() {
  return cfg.applicationKey.length() && cfg.apiKey.length();
}

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
  return wx.valid && observationAgeSeconds() > cfg.staleSeconds;
}

String currentIp() {
  if (WiFi.status() == WL_CONNECTED) return WiFi.localIP().toString();
  if (setupApStarted) return WiFi.softAPIP().toString();
  return String("0.0.0.0");
}

String setupApName() {
  uint64_t chip = ESP.getEfuseMac();
  char suffix[5];
  snprintf(suffix, sizeof(suffix), "%04X", (unsigned int)(chip & 0xFFFF));
  return String(SETUP_AP_PREFIX) + "-" + suffix;
}

String formatClockFromEpoch(time_t t) {
  if (t <= 100000) return "--:--";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  char buf[16];
  strftime(buf, sizeof(buf), "%-I:%M %p", &timeinfo);
  return String(buf);
}

String formatDateFromEpoch(time_t t) {
  if (t <= 100000) return "";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  char buf[32];
  strftime(buf, sizeof(buf), "%a, %b %-d, %Y", &timeinfo);
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
  return formatDateFromEpoch(now);
}

bool fetchAmbientDevices(DynamicJsonDocument &doc, String &errorOut) {
  errorOut = "";
  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!apiConfigured()) {
    errorOut = "Ambient Application Key and API Key are not configured";
    return false;
  }

  String url = String(AMBIENT_DEVICES_URL)
             + "?apiKey=" + urlEncode(cfg.apiKey)
             + "&applicationKey=" + urlEncode(cfg.applicationKey);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(10);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(12000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/4.0");

  respectAmbientRateLimit();

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize HTTPS request";
    return false;
  }

  int code = http.GET();
  lastAmbientRequestMs = millis();
  lastHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Ambient HTTP " + String(code);
    if (body.length()) errorOut += ": " + body;
    http.end();
    return false;
  }

  DeserializationError err = deserializeJson(doc, http.getStream());
  http.end();
  if (err) {
    errorOut = "JSON parse error: " + String(err.c_str());
    return false;
  }
  if (!doc.is<JsonArray>()) {
    errorOut = "Ambient returned an unexpected JSON structure";
    return false;
  }
  if (doc.size() == 0) {
    errorOut = "Ambient account returned no devices";
    return false;
  }
  return true;
}

bool applySelectedDevice(JsonArray devices, bool allowAutoSelect, String &errorOut) {
  JsonObject selected;
  String wanted = normalizeMac(cfg.macAddress);

  for (JsonObject device : devices) {
    String mac = normalizeMac(String((const char*)(device["macAddress"] | "")));
    if (wanted.length() > 0 && mac == wanted) {
      selected = device;
      break;
    }
  }

  if (selected.isNull()) {
    if (wanted.length() == 0 && allowAutoSelect && devices.size() > 0) {
      selected = devices[0].as<JsonObject>();
      cfg.macAddress = normalizeMac(String((const char*)(selected["macAddress"] | "")));
      cfg.stationName = String((const char*)(selected["info"]["name"] | ""));
      saveConfig();
    } else {
      errorOut = "Configured station MAC was not found";
      return false;
    }
  }

  JsonObject last = selected["lastData"].as<JsonObject>();
  if (last.isNull()) {
    errorOut = "Selected station has no lastData";
    return false;
  }

  float temp = tryField(last, "tempf");
  float humidity = tryField(last, "humidity");
  if (!isfinite(temp) || !isfinite(humidity) || humidity < 0 || humidity > 100) {
    errorOut = "Selected station returned invalid tempf/humidity";
    return false;
  }

  wx.tempF = temp;
  wx.humidity = humidity;
  wx.heatIndexF = nwsHeatIndexF(wx.tempF, wx.humidity);
  wx.dewPointF = tryField(last, "dewPoint", "dewPointf");
  if (!isfinite(wx.dewPointF)) wx.dewPointF = dewPointFromTempHumidityF(wx.tempF, wx.humidity);
  wx.windMph = tryField(last, "windspeedmph");
  wx.gustMph = tryField(last, "windgustmph", "gustmph");
  wx.maxDailyGustMph = tryField(last, "maxdailygust");
  wx.windChillF = nwsWindChillF(wx.tempF, wx.windMph);
  wx.windDirDeg = tryField(last, "winddir");
  wx.dateUtcMs = last["dateutc"] | 0ULL;
  wx.fetchedMs = millis();
  wx.valid = true;

  String foundName = String((const char*)(selected["info"]["name"] | ""));
  if (foundName.length() && foundName != cfg.stationName) {
    cfg.stationName = foundName;
    saveConfig();
  }
  return true;
}


static bool sameLocalDay(uint64_t aMs, uint64_t bMs) {
  if (aMs == 0 || bMs == 0) return false;

  time_t a = (time_t)(aMs / 1000ULL);
  time_t b = (time_t)(bMs / 1000ULL);

  struct tm ta;
  struct tm tb;
  localtime_r(&a, &ta);
  localtime_r(&b, &tb);

  return ta.tm_year == tb.tm_year && ta.tm_yday == tb.tm_yday;
}

static void respectAmbientRateLimit() {
  if (lastAmbientRequestMs == 0) return;

  unsigned long elapsed = millis() - lastAmbientRequestMs;
  if (elapsed < 1100UL) {
    unsigned long waitMs = 1100UL - elapsed;
    while (waitMs > 0) {
      unsigned long slice = waitMs > 50UL ? 50UL : waitMs;
      delay(slice);
      if (webStarted) server.handleClient();
      waitMs -= slice;
    }
  }
}

bool fetchAmbientSummary(String &errorOut) {
  errorOut = "";

  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!apiConfigured() || !cfg.macAddress.length()) {
    errorOut = "Ambient credentials/station are not configured";
    return false;
  }
  if (!wx.valid || wx.dateUtcMs == 0) {
    errorOut = "Current observation is not available";
    return false;
  }

  String url = String(AMBIENT_DEVICES_URL) + "/" + cfg.macAddress
             + "?apiKey=" + urlEncode(cfg.apiKey)
             + "&applicationKey=" + urlEncode(cfg.applicationKey)
             + "&limit=288";

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(12);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(15000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/4.0");

  respectAmbientRateLimit();

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize Ambient history HTTPS request";
    return false;
  }

  int code = http.GET();
  lastAmbientRequestMs = millis();
  lastSummaryHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Ambient history HTTP " + String(code);
    if (body.length()) {
      errorOut += ": ";
      errorOut += body;
    }
    http.end();
    return false;
  }

  // Only retain the two fields needed for the mockup summary. This keeps the
  // memory footprint small even when Ambient returns 288 observations.
  StaticJsonDocument<96> filter;
  filter[0]["dateutc"] = true;
  filter[0]["tempf"] = true;

  DynamicJsonDocument doc(18432);
  DeserializationError jsonErr = deserializeJson(
    doc,
    http.getStream(),
    DeserializationOption::Filter(filter)
  );
  http.end();

  if (jsonErr) {
    errorOut = "Ambient history JSON error: " + String(jsonErr.c_str());
    return false;
  }
  if (!doc.is<JsonArray>() || doc.size() == 0) {
    errorOut = "Ambient history returned no observations";
    return false;
  }

  float high = wx.tempF;
  float low = wx.tempF;
  float yesterday = NAN;

  const uint64_t targetYesterdayMs =
    wx.dateUtcMs > 86400000ULL ? wx.dateUtcMs - 86400000ULL : 0ULL;

  uint64_t bestYesterdayDifference = UINT64_MAX;

  for (JsonObject point : doc.as<JsonArray>()) {
    uint64_t pointMs = point["dateutc"] | 0ULL;
    float pointTemp = tryField(point, "tempf");

    if (pointMs == 0 || !isfinite(pointTemp)) continue;

    if (sameLocalDay(pointMs, wx.dateUtcMs)) {
      if (!isfinite(high) || pointTemp > high) high = pointTemp;
      if (!isfinite(low) || pointTemp < low) low = pointTemp;
    }

    if (targetYesterdayMs > 0) {
      uint64_t delta = pointMs > targetYesterdayMs
                     ? pointMs - targetYesterdayMs
                     : targetYesterdayMs - pointMs;

      if (delta < bestYesterdayDifference) {
        bestYesterdayDifference = delta;
        yesterday = pointTemp;
      }
    }
  }

  wx.todayHighF = high;
  wx.todayLowF = low;
  wx.yesterdayTempF = yesterday;
  wx.fromYesterdayF = isfinite(yesterday) ? wx.tempF - yesterday : NAN;
  wx.summaryValid = isfinite(wx.todayHighF) && isfinite(wx.todayLowF);
  wx.summaryFetchedMs = millis();

  return true;
}


bool pollAmbient(bool forceRedraw = true) {
  WeatherData before = wx;
  String stationNameBefore = cfg.stationName;

  DynamicJsonDocument doc(24576);
  String error;

  if (!fetchAmbientDevices(doc, error)) {
    lastApiError = error;
    Serial.println("Ambient poll failed: " + error);
    if (forceRedraw) {
      lastFooterStateKey = "";
      drawFooter();
    }
    return false;
  }

  if (!applySelectedDevice(doc.as<JsonArray>(), true, error)) {
    lastApiError = error;
    Serial.println("Ambient selection failed: " + error);
    if (forceRedraw) {
      lastFooterStateKey = "";
      drawFooter();
    }
    return false;
  }

  lastApiError = "";
  lastPollMs = millis();

  // The mockup shows "From Yesterday" and today's high/low. Ambient's
  // historical endpoint is refreshed less frequently than current data.
  const unsigned long SUMMARY_REFRESH_MS = 300000UL;
  if (lastSummaryPollMs == 0 ||
      millis() - lastSummaryPollMs >= SUMMARY_REFRESH_MS) {
    String summaryError;
    if (fetchAmbientSummary(summaryError)) {
      lastSummaryError = "";
      lastSummaryPollMs = millis();
    } else {
      lastSummaryError = summaryError;
      Serial.println("Ambient summary failed: " + summaryError);
      // Keep the last successful summary on screen.
      lastSummaryPollMs = millis();
    }
  }

  Serial.printf(
    "Ambient: %s temp=%.2fF rh=%.1f%% hi=%.2fF wc=%.2fF dew=%.2fF wind=%.2f gust=%.2f dir=%.1f mode=%s\n",
    cfg.macAddress.c_str(), wx.tempF, wx.humidity, wx.heatIndexF,
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

String pageHead(const String &title) {
  String h;
  h.reserve(1800);
  h += F("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>");
  h += htmlEscape(title);
  h += F("</title><style>");
  h += F("body{font-family:system-ui,-apple-system,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:18px}");
  h += F(".wrap{max-width:760px;margin:auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:18px;margin:14px 0}");
  h += F("h1,h2{margin-top:0}.big{font-size:4rem;font-weight:800;line-height:1}.muted{color:#8b949e}");
  h += F("label{display:block;font-weight:650;margin-top:14px}input{box-sizing:border-box;width:100%;padding:11px;margin-top:5px;background:#0d1117;color:#e6edf3;border:1px solid #484f58;border-radius:8px}");
  h += F("button,.btn{display:inline-block;background:#238636;color:white;border:0;border-radius:8px;padding:10px 14px;text-decoration:none;font-weight:650;cursor:pointer;margin:6px 6px 6px 0}");
  h += F(".secondary{background:#30363d}.danger{background:#b62324}.ok{color:#3fb950}.bad{color:#f85149}code{background:#21262d;padding:2px 5px;border-radius:4px}");
  h += F("table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #30363d;text-align:left}");
  h += F("</style></head><body><div class='wrap'>");
  return h;
}

String pageTail() { return F("</div></body></html>"); }

void handleRoot() {
  String html = pageHead("Apparent Temperature Display");
  html += F("<h1>Apparent Temperature Display</h1><div class='card'>");

  if (wx.valid) {
    html += F("<div class='big'>");
    html += String(apparentOutdoorF(), 1);
    html += F("&deg;F</div>");

    html += F("<p><b>");
    html += apparentTitle();
    html += F("</b> &mdash; <b>");
    html += apparentRiskLabel();
    html += F("</b><br>");

    html += F("Temperature: <b>");
    html += String(wx.tempF, 1);
    html += F("&deg;F</b><br>");

    html += F("Humidity: <b>");
    html += String(wx.humidity, 0);
    html += F("%</b><br>");

    if (isfinite(wx.dewPointF)) {
      html += F("Dew point: <b>");
      html += String(wx.dewPointF, 1);
      html += F("&deg;F</b><br>");
    }

    if (isfinite(wx.windMph)) {
      html += F("Wind: <b>");
      html += String(wx.windMph, 1);
      html += F(" mph</b><br>");
    }

    if (isfinite(wx.fromYesterdayF)) {
      html += F("From yesterday: <b>");
      if (wx.fromYesterdayF >= 0.0f) html += "+";
      html += String(wx.fromYesterdayF, 1);
      html += F("&deg;F</b><br>");
    }

    if (wx.summaryValid) {
      html += F("Today's high / low: <b>");
      html += String(wx.todayHighF, 1);
      html += F("&deg;F / ");
      html += String(wx.todayLowF, 1);
      html += F("&deg;F</b><br>");
    }

    html += F("Observation age: <b>");
    html += String(observationAgeSeconds());
    html += F(" sec</b>");

    if (dataStale()) {
      html += F(" <span class='bad'>(STALE)</span>");
    }
    html += F("</p>");
  } else {
    html += F("<p class='muted'>");
    if (lastApiError.length()) {
      html += htmlEscape(lastApiError);
    } else {
      html += F("Waiting for the first successful AmbientWeather.net poll.");
    }
    html += F("</p>");
  }

  html += F("</div><div class='card'><h2>Status</h2><table>");

  html += F("<tr><th>Wi-Fi</th><td>");
  html += (WiFi.status() == WL_CONNECTED) ? "Connected" : "Not connected";
  html += F("</td></tr>");

  html += F("<tr><th>IP</th><td>");
  html += htmlEscape(currentIp());
  html += F("</td></tr>");

  html += F("<tr><th>Station</th><td>");
  html += htmlEscape(cfg.stationName.length() ? cfg.stationName : String("(auto)"));
  html += F("</td></tr>");

  html += F("<tr><th>MAC</th><td>");
  html += htmlEscape(cfg.macAddress.length() ? cfg.macAddress : String("(auto)"));
  html += F("</td></tr>");

  html += F("<tr><th>Timezone</th><td><code>");
  html += htmlEscape(cfg.timezoneTz);
  html += F("</code></td></tr>");

  html += F("<tr><th>Poll interval</th><td>");
  html += String(cfg.pollSeconds);
  html += F(" sec</td></tr>");

  html += F("<tr><th>Ambient API</th><td>");
  html += apiConfigured() ? "Configured" : "Not configured";
  html += F("</td></tr>");

  if (lastHttpCode) {
    html += F("<tr><th>Last HTTP code</th><td>");
    html += String(lastHttpCode);
    html += F("</td></tr>");
  }

  if (lastSummaryHttpCode) {
    html += F("<tr><th>History HTTP code</th><td>");
    html += String(lastSummaryHttpCode);
    html += F("</td></tr>");
  }
  if (lastSummaryError.length()) {
    html += F("<tr><th>History warning</th><td class='bad'>");
    html += htmlEscape(lastSummaryError);
    html += F("</td></tr>");
  }

  if (lastApiError.length()) {
    html += F("<tr><th>Last API error</th><td class='bad'>");
    html += htmlEscape(lastApiError);
    html += F("</td></tr>");
  }

  html += F("</table></div>");
  html += F("<a class='btn' href='/config'>Configuration</a>");
  html += F("<a class='btn secondary' href='/discover'>Discover stations</a>");
  html += F("<a class='btn secondary' href='/poll'>Poll now</a>");
  html += F("<a class='btn secondary' href='/status'>JSON</a>");
  html += pageTail();

  server.send(200, "text/html", html);
}

void handleConfig() {
  String html = pageHead("Configuration");
  html += F("<h1>Configuration</h1>");
  html += F("<div class='card'><b>Persistent settings:</b> values saved here override any compile-time first-boot defaults and remain active across reboots. Factory Reset clears them and allows the compiled defaults to seed again.</div>");

  if (setupApStarted) {
    html += F("<div class='card'><b>Setup access point active.</b><br>");
    html += F("Connect to the ESP32 setup network, enter Wi-Fi and Ambient settings below, save, and the device will reboot.</div>");
  }

  html += F("<form method='post' action='/save'>");
  html += F("<div class='card'><h2>Wi-Fi</h2>");

  html += F("<label>Wi-Fi SSID<input name='ssid' maxlength='32' value='");
  html += htmlEscape(cfg.ssid);
  html += F("' required></label>");

  html += F("<label>Wi-Fi password<input type='password' name='wpass' maxlength='64' placeholder='Leave blank to keep saved password'></label>");

  html += F("<label>Hostname<input name='host' maxlength='32' value='");
  html += htmlEscape(cfg.hostname);
  html += F("'></label>");

  html += F("<label>Timezone (POSIX TZ string)<input name='tz' maxlength='96' value='");
  html += htmlEscape(cfg.timezoneTz);
  html += F("'></label>");
  html += F("</div>");

  html += F("<div class='card'><h2>AmbientWeather.net</h2>");
  html += F("<p class='muted'>Ambient requires both an Application Key and an API Key. Saved secrets are never rendered back into the page.</p>");

  html += F("<label>Application Key<input type='password' name='appkey' maxlength='128' placeholder='");
  if (cfg.applicationKey.length()) {
    html += F("Saved — leave blank to keep");
  } else {
    html += F("Enter applicationKey");
  }
  html += F("'></label>");

  html += F("<label>API Key / Device Key<input type='password' name='apikey' maxlength='128' placeholder='");
  if (cfg.apiKey.length()) {
    html += F("Saved — leave blank to keep");
  } else {
    html += F("Enter apiKey");
  }
  html += F("'></label>");

  html += F("<label>Station MAC address<input name='mac' maxlength='32' value='");
  html += htmlEscape(cfg.macAddress);
  html += F("' placeholder='Leave blank to auto-select first station'></label>");

  html += F("<label>Poll interval (seconds)<input type='number' min='");
  html += String(MIN_POLL_SECONDS);
  html += F("' max='3600' name='poll' value='");
  html += String(cfg.pollSeconds);
  html += F("'></label>");

  html += F("<label>Mark data stale after (seconds)<input type='number' min='");
  html += String(MIN_STALE_SECONDS);
  html += F("' max='86400' name='stale' value='");
  html += String(cfg.staleSeconds);
  html += F("'></label>");

  html += F("</div><button type='submit'>Save &amp; reboot</button>");
  html += F("<a class='btn secondary' href='/'>Cancel</a></form>");

  html += F("<div class='card'><h2>Credential management</h2>");
  html += F("<form method='post' action='/clear-ambient' onsubmit=\"return confirm('Clear saved Ambient credentials and station selection?')\">");
  html += F("<button class='danger' type='submit'>Clear Ambient credentials</button></form>");
  html += F("<form method='post' action='/factory-reset' onsubmit=\"return confirm('Erase all settings including Wi-Fi?')\">");
  html += F("<button class='danger' type='submit'>Factory reset</button></form>");
  html += F("</div>");

  html += pageTail();
  server.send(200, "text/html", html);
}


void handleSave() {
  if (server.hasArg("ssid")) cfg.ssid = server.arg("ssid");
  if (server.hasArg("wpass") && server.arg("wpass").length()) cfg.wifiPassword = server.arg("wpass");
  if (server.hasArg("host")) {
    String h = server.arg("host");
    h.trim();
    if (h.length()) cfg.hostname = h;
  }
  if (server.hasArg("tz")) {
    String tz = server.arg("tz");
    tz.trim();
    if (tz.length()) cfg.timezoneTz = tz;
  }
  if (server.hasArg("appkey") && server.arg("appkey").length()) cfg.applicationKey = server.arg("appkey");
  if (server.hasArg("apikey") && server.arg("apikey").length()) cfg.apiKey = server.arg("apikey");
  if (server.hasArg("mac")) cfg.macAddress = normalizeMac(server.arg("mac"));
  if (server.hasArg("poll")) {
    uint32_t p = (uint32_t)server.arg("poll").toInt();
    if (p < MIN_POLL_SECONDS) p = MIN_POLL_SECONDS;
    if (p > 3600UL) p = 3600UL;
    cfg.pollSeconds = p;
  }
  if (server.hasArg("stale")) {
    uint32_t s = (uint32_t)server.arg("stale").toInt();
    if (s < MIN_STALE_SECONDS) s = MIN_STALE_SECONDS;
    if (s > 86400UL) s = 86400UL;
    cfg.staleSeconds = s;
  }
  cfg.stationName = "";
  saveConfig();

  String html = pageHead("Saved");
  html += F("<div class='card'><h1>Settings saved</h1><p>The device is rebooting.</p></div>");
  html += pageTail();
  server.send(200, "text/html", html);
  delay(900);
  ESP.restart();
}

void handleClearAmbient() {
  cfg.applicationKey = "";
  cfg.apiKey = "";
  cfg.macAddress = "";
  cfg.stationName = "";
  saveConfig();
  server.sendHeader("Location", "/config");
  server.send(303);
}

void handleFactoryReset() {
  prefs.begin("heatidx", false);
  prefs.clear();
  prefs.end();
  String html = pageHead("Factory reset");
  html += F("<div class='card'><h1>Settings erased</h1><p>NVS was cleared. On reboot the compiled first-boot defaults will be seeded again; if no Wi-Fi default is compiled, setup mode will be used.</p></div>");
  html += pageTail();
  server.send(200, "text/html", html);
  delay(900);
  ESP.restart();
}

void handlePollNow() {
  bool ok = pollAmbient(true);

  if (ok) {
    server.sendHeader("Location", "/");
    server.send(303);
  } else {
    String html = pageHead("Poll failed");
    html += F("<div class='card'><h1>Ambient poll failed</h1><p class='bad'>");
    html += htmlEscape(lastApiError);
    html += F("</p><a class='btn secondary' href='/'>Back</a></div>");
    html += pageTail();
    server.send(502, "text/html", html);
  }
}


void handleDiscover() {
  String html = pageHead("Discover stations");
  html += F("<h1>Ambient stations</h1>");

  if (!apiConfigured()) {
    html += F("<div class='card'><p>Configure your Ambient keys first.</p>");
    html += F("<a class='btn' href='/config'>Configuration</a></div>");
    html += pageTail();
    server.send(400, "text/html", html);
    return;
  }

  DynamicJsonDocument doc(24576);
  String error;

  if (!fetchAmbientDevices(doc, error)) {
    lastApiError = error;
    html += F("<div class='card'><p class='bad'>");
    html += htmlEscape(error);
    html += F("</p></div>");
    html += pageTail();
    server.send(502, "text/html", html);
    return;
  }

  html += F("<div class='card'><table>");
  html += F("<tr><th>Name</th><th>Location</th><th>MAC</th><th></th></tr>");

  for (JsonObject device : doc.as<JsonArray>()) {
    String mac = normalizeMac(String((const char*)(device["macAddress"] | "")));
    String name = String((const char*)(device["info"]["name"] | ""));
    String location = String((const char*)(device["info"]["location"] | ""));

    html += F("<tr><td>");
    html += htmlEscape(name);
    html += F("</td><td>");
    html += htmlEscape(location);
    html += F("</td><td><code>");
    html += htmlEscape(mac);
    html += F("</code></td><td>");

    html += F("<form method='post' action='/select' style='margin:0'>");
    html += F("<input type='hidden' name='mac' value='");
    html += htmlEscape(mac);
    html += F("'>");
    html += F("<input type='hidden' name='name' value='");
    html += htmlEscape(name);
    html += F("'>");
    html += F("<button type='submit'>Select</button></form>");
    html += F("</td></tr>");
  }

  html += F("</table></div>");
  html += F("<a class='btn secondary' href='/'>Back</a>");
  html += pageTail();
  server.send(200, "text/html", html);
}


void handleSelect() {
  if (!server.hasArg("mac")) {
    server.send(400, "text/plain", "Missing station MAC");
    return;
  }
  cfg.macAddress = normalizeMac(server.arg("mac"));
  cfg.stationName = server.hasArg("name") ? server.arg("name") : "";
  saveConfig();
  lastPollMs = 0;
  lastSummaryPollMs = 0;
  wx.summaryValid = false;
  wx.yesterdayTempF = NAN;
  wx.fromYesterdayF = NAN;
  wx.todayHighF = NAN;
  wx.todayLowF = NAN;
  pollAmbient(true);
  server.sendHeader("Location", "/");
  server.send(303);
}

String jsonStatus() {
  String s;
  s.reserve(900);
  s += "{";
  s += "\"wifi_connected\":";
  s += (WiFi.status() == WL_CONNECTED ? "true" : "false");
  s += ",\"setup_ap\":";
  s += (setupApStarted ? "true" : "false");
  s += ",\"ip\":\"" + currentIp() + "\"";
  s += ",\"api_configured\":";
  s += (apiConfigured() ? "true" : "false");
  s += ",\"station_mac\":\"" + cfg.macAddress + "\"";
  s += ",\"station_name\":\"" + cfg.stationName + "\"";
  s += ",\"poll_seconds\":" + String(cfg.pollSeconds);
  s += ",\"stale_seconds\":" + String(cfg.staleSeconds);
  s += ",\"last_http_code\":" + String(lastHttpCode);
  s += ",\"last_api_error\":\"" + lastApiError + "\"";
  s += ",\"valid\":";
  s += (wx.valid ? "true" : "false");
  if (wx.valid) {
    s += ",\"tempf\":" + String(wx.tempF, 2);
    s += ",\"humidity\":" + String(wx.humidity, 1);
    s += ",\"heat_index_f\":";
    s += String(wx.heatIndexF, 2);
    s += ",\"wind_chill_f\":";
    s += String(wx.windChillF, 2);
    s += ",\"apparent_f\":";
    s += String(apparentOutdoorF(), 2);
    s += ",\"mode\":\"";
    s += apparentTitle();
    s += "\"";
    s += ",\"dew_point_f\":";
    s += String(wx.dewPointF, 2);
    s += ",\"wind_mph\":" + String(wx.windMph, 2);
    s += ",\"gust_mph\":" + String(wx.gustMph, 2);
    s += ",\"maxdailygust_mph\":" + String(wx.maxDailyGustMph, 2);
    s += ",\"wind_dir_deg\":" + String(wx.windDirDeg, 1);
    if (isfinite(wx.yesterdayTempF)) {
      s += ",\"yesterday_temp_f\":" + String(wx.yesterdayTempF, 2);
    }
    if (isfinite(wx.fromYesterdayF)) {
      s += ",\"from_yesterday_f\":" + String(wx.fromYesterdayF, 2);
    }
    if (wx.summaryValid) {
      s += ",\"today_high_f\":" + String(wx.todayHighF, 2);
      s += ",\"today_low_f\":" + String(wx.todayLowF, 2);
    }
    s += ",\"observation_age_seconds\":" + String(observationAgeSeconds());
    s += ",\"stale\":";
    s += (dataStale() ? "true" : "false");
  }
  s += "}";
  return s;
}

void startWebServer() {
  if (webStarted) return;
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, [](){ server.send(200, "application/json", jsonStatus()); });
  server.on("/config", HTTP_GET, handleConfig);
  server.on("/save", HTTP_POST, handleSave);
  server.on("/discover", HTTP_GET, handleDiscover);
  server.on("/select", HTTP_POST, handleSelect);
  server.on("/poll", HTTP_GET, handlePollNow);
  server.on("/clear-ambient", HTTP_POST, handleClearAmbient);
  server.on("/factory-reset", HTTP_POST, handleFactoryReset);
  server.onNotFound([](){ server.send(404, "text/plain", "Not found"); });
  server.begin();
  webStarted = true;
  Serial.println("Web UI started on port 80");
}

void startSetupAp() {
  if (setupApStarted) return;
  WiFi.mode(WIFI_AP_STA);
  String name = setupApName();
  if (WiFi.softAP(name.c_str())) {
    setupApStarted = true;
    Serial.print("Setup AP: ");
    Serial.println(name);
    Serial.print("Setup IP: ");
    Serial.println(WiFi.softAPIP());
  }
  startWebServer();
  drawWaitingScreen();
}

bool connectWifi() {
  if (!cfg.ssid.length()) return false;
  WiFi.mode(setupApStarted ? WIFI_AP_STA : WIFI_STA);
  WiFi.setHostname(cfg.hostname.c_str());
  WiFi.begin(cfg.ssid.c_str(), cfg.wifiPassword.c_str());

  Serial.printf("Connecting to Wi-Fi '%s'...\n", cfg.ssid.c_str());
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    server.handleClient();
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected: ");
    Serial.println(WiFi.localIP());
    configTzTime(cfg.timezoneTz.c_str(), "pool.ntp.org", "time.nist.gov");
    startWebServer();

    if (setupApStarted) {
      WiFi.softAPdisconnect(true);
      setupApStarted = false;
      WiFi.mode(WIFI_STA);
    }
    drawWaitingScreen();
    return true;
  }

  Serial.println("Wi-Fi connection timed out");
  return false;
}

void commonSetup() {
  loadConfig();
  startWebServer();

  if (!cfg.ssid.length()) {
    startSetupAp();
    return;
  }
  if (!connectWifi()) {
    startSetupAp();
    return;
  }
  if (!apiConfigured()) {
    lastApiError = "Configure Ambient API credentials at /config";
    drawWaitingScreen();
    return;
  }
  pollAmbient(true);
}


static bool floatDifferent(float a, float b, float tolerance = 0.01f) {
  if (isnan(a) && isnan(b)) return false;
  if (isnan(a) != isnan(b)) return true;
  return fabsf(a - b) > tolerance;
}

static bool weatherDisplayChanged(const WeatherData &before, const WeatherData &after) {
  if (before.valid != after.valid) return true;
  if (!after.valid) return false;

  if (before.dateUtcMs != after.dateUtcMs) return true;
  if (floatDifferent(before.tempF, after.tempF)) return true;
  if (floatDifferent(before.humidity, after.humidity)) return true;
  if (floatDifferent(before.heatIndexF, after.heatIndexF)) return true;
  if (floatDifferent(before.windChillF, after.windChillF)) return true;
  if (floatDifferent(before.dewPointF, after.dewPointF)) return true;
  if (floatDifferent(before.windMph, after.windMph)) return true;
  if (floatDifferent(before.gustMph, after.gustMph)) return true;
  if (floatDifferent(before.windDirDeg, after.windDirDeg)) return true;
  if (floatDifferent(before.yesterdayTempF, after.yesterdayTempF)) return true;
  if (floatDifferent(before.fromYesterdayF, after.fromYesterdayF)) return true;
  if (floatDifferent(before.todayHighF, after.todayHighF)) return true;
  if (floatDifferent(before.todayLowF, after.todayLowF)) return true;
  if (before.summaryValid != after.summaryValid) return true;

  return false;
}

String footerStateKey() {
  String key;
  key.reserve(160);

  key += String((int)WiFi.status());
  key += '|';
  key += setupApStarted ? '1' : '0';
  key += '|';
  key += apiConfigured() ? '1' : '0';
  key += '|';
  key += wx.valid ? '1' : '0';
  key += '|';
  key += dataStale() ? '1' : '0';
  key += '|';
  key += updateClockText();
  key += '|';
  key += lastApiError;

  return key;
}

void commonLoop() {
  if (webStarted) {
    server.handleClient();
  }

  const unsigned long nowMs = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (!cfg.ssid.length()) {
      if (!setupApStarted) {
        startSetupAp();
      }
    } else if (nowMs - lastWifiAttemptMs >= WIFI_RETRY_SECONDS * 1000UL) {
      lastWifiAttemptMs = nowMs;
      if (!connectWifi() && !setupApStarted) {
        startSetupAp();
      }
    }
  } else if (apiConfigured()) {
    if (lastPollMs == 0 || nowMs - lastPollMs >= cfg.pollSeconds * 1000UL) {
      lastPollMs = nowMs;
      pollAmbient(true);
    }
  }

  // Check UI state periodically, but only write to the display when the
  // visible footer state actually changed.
  if (nowMs - lastUiStateCheckMs >= 1000UL) {
    lastUiStateCheckMs = nowMs;
    String newKey = footerStateKey();
    if (newKey != lastFooterStateKey) {
      lastFooterStateKey = newKey;
      drawFooter();
    }
  }

  // 20 ms keeps the web UI responsive without spinning the application
  // loop roughly 500 times per second while idle.
  delay(20);
}

#include <LovyanGFX.hpp>

// -----------------------------------------------------------------------------
// Native LILYGO T-Display-S3 LovyanGFX profile.
//
// The production firmware defines the board profile directly instead of using
// LilyGo-display-library. This avoids version coupling between that wrapper
// and LovyanGFX's ESP32-S3 Parallel8 implementation.
// -----------------------------------------------------------------------------
class WS5000_TDisplayS3 : public lgfx::LGFX_Device {
  lgfx::Panel_ST7789 _panel;
  lgfx::Bus_Parallel8 _bus;
  lgfx::Light_PWM _light;

public:
  WS5000_TDisplayS3() {
    {
      auto cfg = _bus.config();

      cfg.freq_write = 20000000;

      cfg.pin_wr = 8;
      cfg.pin_rd = 9;
      cfg.pin_rs = 7;

      cfg.pin_d0 = 39;
      cfg.pin_d1 = 40;
      cfg.pin_d2 = 41;
      cfg.pin_d3 = 42;
      cfg.pin_d4 = 45;
      cfg.pin_d5 = 46;
      cfg.pin_d6 = 47;
      cfg.pin_d7 = 48;

      _bus.config(cfg);
      _panel.setBus(&_bus);
    }

    {
      auto cfg = _panel.config();

      cfg.pin_cs = 6;
      cfg.pin_rst = 5;
      cfg.pin_busy = -1;

      cfg.panel_width = 170;
      cfg.panel_height = 320;
      cfg.offset_x = 35;
      cfg.offset_y = 0;
      cfg.offset_rotation = 0;

      cfg.dummy_read_pixel = 8;
      cfg.dummy_read_bits = 1;

      cfg.readable = false;
      cfg.invert = true;
      cfg.rgb_order = false;
      cfg.dlen_16bit = false;
      cfg.bus_shared = true;

      _panel.config(cfg);
    }

    {
      auto cfg = _light.config();

      cfg.pin_bl = 38;
      cfg.invert = false;
      cfg.freq = 44100;
      cfg.pwm_channel = 0;

      _light.config(cfg);
      _panel.setLight(&_light);
    }

    setPanel(&_panel);
  }
};

WS5000_TDisplayS3 display;

static const uint16_t C_BLACK = 0x0000;
static const uint16_t C_WHITE = 0xFFFF;

static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return display.color565(r, g, b);
}

struct RiskStyle {
  const char *label;
  uint16_t panel;
  uint16_t status;
};

RiskStyle riskFor(float apparentF) {
  if (windChillApplies()) {
    if (apparentF <= -35.0f) return {"EXTREME DANGER", rgb565(16, 78, 185), rgb565(8, 48, 125)};
    if (apparentF <= -20.0f) return {"DANGER", rgb565(20, 105, 215), rgb565(10, 62, 150)};
    if (apparentF <= 0.0f)   return {"VERY COLD", rgb565(22, 125, 230), rgb565(12, 75, 165)};
    if (apparentF <= 20.0f)  return {"COLD", rgb565(25, 140, 240), rgb565(14, 82, 175)};
    return {"CHILLY", rgb565(35, 150, 240), rgb565(18, 92, 180)};
  }
  if (apparentF >= 125.0f) return {"EXTREME DANGER", rgb565(205, 25, 55), rgb565(135, 10, 35)};
  if (apparentF >= 103.0f) return {"DANGER", rgb565(235, 35, 30), rgb565(170, 20, 15)};
  if (apparentF >= 90.0f)  return {"EXTREME CAUTION", rgb565(240, 105, 15), rgb565(165, 60, 5)};
  if (apparentF >= 80.0f)  return {"CAUTION", rgb565(240, 165, 20), rgb565(165, 100, 5)};
  return {"NORMAL", rgb565(35, 130, 75), rgb565(15, 82, 42)};
}

static void drawIconBitmap(int x, int y, const uint16_t *icon) {
  for (int iy = 0; iy < UI_ICON_H; iy++) {
    for (int ix = 0; ix < UI_ICON_W; ix++) {
      uint16_t px = pgm_read_word(&icon[iy * UI_ICON_W + ix]);
      if (px != UI_ICON_TRANSPARENT) display.drawPixel(x + ix, y + iy, px);
    }
  }
}

void drawWiFiIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_WIFI); }
void drawThermometer(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y, ICON_THERMOMETER); }
void drawDrop(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y, ICON_DROP); }
void drawWindIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y - 2, ICON_WIND); }
void drawCompassIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_COMPASS); }
void drawLeafIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_LEAF); }
void drawTrendIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y, ICON_TREND); }
void drawSunIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_SUN); }

void drawMetricCard(int x, int y, int w, int h) {
  uint16_t bg = rgb565(2, 25, 43);
  uint16_t border = rgb565(10, 63, 100);
  display.fillRoundRect(x, y, w, h, 7, bg);
  display.drawRoundRect(x, y, w, h, 7, border);
}

String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s;
  if (value >= 0.0f) s += "+";
  s += String(value, 1);
  s += "F";
  return s;
}


void drawHeader() {
  display.setTextColor(C_WHITE, C_BLACK);
  display.setTextDatum(textdatum_t::middle_left);

  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() <= 12) {
    display.setFont(&fonts::Font4);
  } else {
    display.setFont(&fonts::Font2);
    if (station.length() > 18) station = station.substring(0, 18);
  }

  // Production V6: station name only. Do not show a live/current clock in
  // the T-Display header. The footer's "Updated ..." value is the weather
  // observation timestamp and is intentionally retained.
  display.drawString(station, 8, 24);
  display.drawFastHLine(8, 48, 154, rgb565(45, 205, 235));
}

void drawFooter() {
  uint16_t bg = rgb565(4, 31, 51);
  uint16_t border = rgb565(10, 63, 100);

  display.fillRect(0, 290, 170, 30, C_BLACK);
  display.fillRoundRect(8, 294, 154, 22, 6, bg);
  display.drawRoundRect(8, 294, 154, 22, 6, border);

  display.setFont(&fonts::Font0);
  display.setTextDatum(textdatum_t::middle_center);
  display.setTextColor(C_WHITE, bg);

  if (WiFi.status() != WL_CONNECTED) {
    display.drawString(setupApStarted ? "Setup 192.168.4.1" : "Wi-Fi disconnected", 85, 305);
    return;
  }
  if (!apiConfigured()) {
    display.drawString("Open /config", 85, 305);
    return;
  }
  if (!wx.valid) {
    display.setTextColor(lastApiError.length() ? rgb565(255, 105, 90) : C_WHITE, bg);
    display.drawString(lastApiError.length() ? "Ambient API error" : "Fetching Ambient...", 85, 305);
    return;
  }

  String footer = "Updated ";
  footer += updateClockText();
  if (dataStale()) {
    footer = "STALE - " + footer;
    display.setTextColor(rgb565(255, 105, 90), bg);
  }
  display.drawString(footer, 85, 305);
}

void drawWaitingScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  display.setTextDatum(textdatum_t::middle_center);
  display.setTextColor(C_WHITE, C_BLACK);
  display.setFont(&fonts::Font4);
  display.drawString(setupApStarted ? "SETUP" : "WAITING", 85, 112);

  display.setFont(&fonts::Font2);
  display.setTextColor(rgb565(175, 182, 192), C_BLACK);
  if (setupApStarted) {
    display.drawString("Connect to setup Wi-Fi", 85, 148);
    display.setFont(&fonts::Font0);
    display.setTextColor(rgb565(65, 205, 255), C_BLACK);
    display.drawString(setupApName(), 85, 180);
    display.drawString("192.168.4.1/config", 85, 198);
  } else if (WiFi.status() == WL_CONNECTED) {
    display.drawString(apiConfigured() ? "AmbientWeather.net" : "API setup needed", 85, 150);
    display.setFont(&fonts::Font0);
    display.setTextColor(rgb565(65, 205, 255), C_BLACK);
    display.drawString(WiFi.localIP().toString(), 85, 184);
    display.drawString("/config", 85, 202);
  } else {
    display.drawString("Connecting to Wi-Fi", 85, 154);
  }

  drawFooter();
}

void drawWeatherScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  const uint16_t cyan = rgb565(65, 205, 255);
  const uint16_t muted = rgb565(165, 190, 205);
  const uint16_t green = rgb565(120, 225, 70);
  const uint16_t yellow = rgb565(255, 195, 25);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);

  // Main HEAT INDEX / WIND CHILL card
  display.fillRoundRect(8, 54, 154, 88, 10, risk.panel);

  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, risk.panel);
  display.drawString(apparentTitle(), 85, 66);

  String value = String((int)lroundf(apparentF));
  display.setFont(&fonts::Font7);
  display.drawString(value, 73, 96);

  int valueWidth = display.textWidth(value);
  int rightEdge = 73 + valueWidth / 2;
  display.drawCircle(rightEdge + 5, 81, 3, C_WHITE);

  display.setFont(&fonts::Font4);
  display.drawString("F", rightEdge + 17, 103);

  display.fillRoundRect(16, 118, 138, 18, 6, risk.status);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, risk.status);
  display.drawString(apparentRiskLabel(), 85, 127);

  // Temperature / Humidity
  drawMetricCard(7, 147, 77, 34);
  drawThermometer(13, 151, rgb565(255, 70, 55));
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, rgb565(2, 25, 43));
  String tempText = String(wx.tempF, 1) + "F";
  display.drawString(tempText, 29, 158);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, rgb565(2, 25, 43));
  display.drawString("Temp", 29, 174);

  drawMetricCard(87, 147, 76, 34);
  drawDrop(99, 151, rgb565(50, 165, 255));
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, rgb565(2, 25, 43));
  display.drawString(String((int)lroundf(wx.humidity)) + "%", 113, 158);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, rgb565(2, 25, 43));
  display.drawString("Humidity", 113, 174);

  // Dew point / From Yesterday
  drawMetricCard(7, 184, 77, 34);
  drawLeafIcon(19, 197, green);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, rgb565(2, 25, 43));
  display.drawString(isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + "F" : "--", 31, 195);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, rgb565(2, 25, 43));
  display.drawString("Dew Point", 31, 211);

  drawMetricCard(87, 184, 76, 34);
  drawTrendIcon(94, 193, cyan);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, rgb565(2, 25, 43));
  display.drawString(signedTempDelta(wx.fromYesterdayF), 113, 195);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, rgb565(2, 25, 43));
  display.drawString("From Yesterday", 94, 211);

  // Wind / Direction
  drawMetricCard(7, 221, 77, 34);
  drawWindIcon(13, 232, cyan);
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, rgb565(2, 25, 43));
  display.drawString(isfinite(wx.windMph) ? String(wx.windMph, 1) + " mph" : "--", 32, 231);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, rgb565(2, 25, 43));
  display.drawString(isfinite(wx.gustMph) ? "Gust " + String(wx.gustMph, 1) : "Wind", 32, 247);

  drawMetricCard(87, 221, 76, 34);
  drawCompassIcon(100, 238, rgb565(225, 235, 245));
  display.setFont(&fonts::Font2);
  display.setTextColor(C_WHITE, rgb565(2, 25, 43));
  String degText = isfinite(wx.windDirDeg) ? String((int)lroundf(wx.windDirDeg)) + String("\xB0") : "--";
  display.drawString(degText, 115, 231);
  display.setFont(&fonts::Font0);
  display.setTextColor(cyan, rgb565(2, 25, 43));
  display.drawString(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "Direction", 115, 247);

  // Today's high / low card
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

  drawFooter();
}


void setup() {
  Serial.begin(115200);
  delay(250);

  display.init();
  display.setRotation(0);
  display.setBrightness(255);
  display.fillScreen(C_BLACK);

  drawWaitingScreen();
  commonSetup();
  lastFooterStateKey = footerStateKey();
}

void loop() {
  commonLoop();
}
