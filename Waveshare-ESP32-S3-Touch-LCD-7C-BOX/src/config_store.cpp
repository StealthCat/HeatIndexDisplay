#include "app_state.h"
#include "config_store.h"
#include "compile_defaults.h"

String normalizeMac(String mac) {
  mac.trim();
  mac.toUpperCase();
  mac.replace("-", ":");
  return mac;
}

String normalizeStationId(String stationId) {
  stationId.trim();
  stationId.toUpperCase();
  return stationId;
}

String normalizeWeatherSource(String source) {
  source.trim();
  source.toLowerCase();
  if (source == "wunderground" || source == "wu" || source == "weatherunderground") {
    return "wunderground";
  }
  return "ambient";
}

bool usingAmbientWeather() {
  return normalizeWeatherSource(cfg.weatherSource) == "ambient";
}

bool usingWeatherUnderground() {
  return normalizeWeatherSource(cfg.weatherSource) == "wunderground";
}

String weatherSourceLabel() {
  return usingWeatherUnderground() ? String("Weather Underground") : String("Ambient Weather");
}

void applyCompileTimeDefaults() {
  cfg.ssid = String(COMPILED_WIFI_SSID);
  cfg.wifiPassword = String(COMPILED_WIFI_PASSWORD);
  cfg.weatherSource = normalizeWeatherSource(String(COMPILED_WEATHER_SOURCE));
  cfg.applicationKey = String(COMPILED_AMBIENT_APPLICATION_KEY);
  cfg.apiKey = String(COMPILED_AMBIENT_API_KEY);
  cfg.macAddress = normalizeMac(String(COMPILED_AMBIENT_STATION_MAC));
  cfg.wuApiKey = String(COMPILED_WUNDERGROUND_API_KEY);
  cfg.wuStationId = normalizeStationId(String(COMPILED_WUNDERGROUND_STATION_ID));
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

  // Migration support for firmware versions before V7.4/V7.7. Existing
  // Ambient-only installations default to Ambient Weather when no source key
  // is present, preserving their current behavior and credentials.
  const bool legacyConfigPresent =
      prefs.isKey("ssid")      ||
      prefs.isKey("wpass")     ||
      prefs.isKey("source")    ||
      prefs.isKey("appkey")    ||
      prefs.isKey("apikey")    ||
      prefs.isKey("mac")       ||
      prefs.isKey("wuapikey")  ||
      prefs.isKey("wustation") ||
      prefs.isKey("stname")    ||
      prefs.isKey("host")      ||
      prefs.isKey("tz")        ||
      prefs.isKey("poll")      ||
      prefs.isKey("stale");

  if (initialized || legacyConfigPresent) {
    cfg.ssid = prefs.getString("ssid", "");
    cfg.wifiPassword = prefs.getString("wpass", "");
    cfg.weatherSource = normalizeWeatherSource(prefs.getString("source", "ambient"));
    cfg.applicationKey = prefs.getString("appkey", "");
    cfg.apiKey = prefs.getString("apikey", "");
    cfg.macAddress = normalizeMac(prefs.getString("mac", ""));
    cfg.wuApiKey = prefs.getString("wuapikey", "");
    cfg.wuStationId = normalizeStationId(prefs.getString("wustation", ""));
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

    if (!initialized && legacyConfigPresent) {
      saveConfig();
    }
    return;
  }

  prefs.end();

  applyCompileTimeDefaults();
  saveConfig();

  Serial.println("Seeded first-boot configuration from compile_defaults.h");
}

void saveConfig() {
  prefs.begin("heatidx", false);
  prefs.putBool("cfginit", true);
  prefs.putString("ssid", cfg.ssid);
  prefs.putString("wpass", cfg.wifiPassword);
  prefs.putString("source", normalizeWeatherSource(cfg.weatherSource));
  prefs.putString("appkey", cfg.applicationKey);
  prefs.putString("apikey", cfg.apiKey);
  prefs.putString("mac", normalizeMac(cfg.macAddress));
  prefs.putString("wuapikey", cfg.wuApiKey);
  prefs.putString("wustation", normalizeStationId(cfg.wuStationId));
  prefs.putString("stname", cfg.stationName);
  prefs.putString("host", cfg.hostname);
  prefs.putString("tz", cfg.timezoneTz);
  prefs.putUInt("poll", cfg.pollSeconds);
  prefs.putUInt("stale", cfg.staleSeconds);
  prefs.end();
}

bool ambientConfigured() {
  return cfg.applicationKey.length() && cfg.apiKey.length();
}

bool weatherUndergroundConfigured() {
  return cfg.wuApiKey.length() && cfg.wuStationId.length();
}

bool apiConfigured() {
  return usingWeatherUnderground() ? weatherUndergroundConfigured() : ambientConfigured();
}
