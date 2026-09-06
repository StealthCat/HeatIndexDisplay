
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

