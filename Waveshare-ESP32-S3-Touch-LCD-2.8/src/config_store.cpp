#include "app_state.h"
#include "config_store.h"
#include "compile_defaults.h"

String normalizeMac(String mac) {
  mac.trim();
  mac.toUpperCase();
  mac.replace("-", ":");
  return mac;
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
