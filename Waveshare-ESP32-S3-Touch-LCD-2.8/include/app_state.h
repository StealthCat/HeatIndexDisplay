#pragma once
#include <Arduino.h>
#include <WebServer.h>
#include <Preferences.h>
#include "config.h"

struct AppConfig {
  String ssid;
  String wifiPassword;
  String weatherSource = "ambient";
  String applicationKey;
  String apiKey;
  String macAddress;
  String wuApiKey;
  String wuStationId;
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

extern WebServer server;
extern Preferences prefs;
extern AppConfig cfg;
extern WeatherData wx;

extern bool webStarted;
extern bool setupApStarted;
extern unsigned long lastWifiAttemptMs;
extern unsigned long lastPollMs;
extern unsigned long lastSummaryPollMs;
extern unsigned long lastAmbientRequestMs;
extern unsigned long lastUiStateCheckMs;
extern String lastFooterStateKey;
extern String lastApiError;
extern int lastHttpCode;
extern int lastSummaryHttpCode;
extern String lastSummaryError;
