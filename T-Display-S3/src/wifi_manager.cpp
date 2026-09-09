#include <WiFi.h>
#include <time.h>
#include "app_state.h"
#include "wifi_manager.h"
#include "config.h"
#include "display_ui.h"
#include "web_ui.h"

static const char* wifiStatusLabel(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS: return "idle";
    case WL_NO_SSID_AVAIL: return "SSID not found";
    case WL_SCAN_COMPLETED: return "scan completed";
    case WL_CONNECTED: return "connected";
    case WL_CONNECT_FAILED: return "connect failed";
    case WL_CONNECTION_LOST: return "connection lost";
    case WL_DISCONNECTED: return "disconnected";
    default: return "unknown";
  }
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

void startSetupAp() {
  if (setupApStarted) return;

  Serial.println("Entering dedicated setup AP mode");

  // Failsafe setup mode must be stable and independent of a failing station
  // association. Completely stop STA/reconnect activity before starting a
  // dedicated AP. Stored application credentials live in Preferences and are
  // not erased by this radio reset.
  WiFi.setAutoReconnect(false);
  WiFi.softAPdisconnect(true);
  WiFi.disconnect(true, false);
  delay(250);

  if (!WiFi.mode(WIFI_AP)) {
    Serial.println("Failed to enter WIFI_AP mode for setup AP");
    drawFooter();
    return;
  }
  delay(100);

  String name = setupApName();
  bool started = false;
  for (uint8_t attempt = 1; attempt <= 3 && !started; ++attempt) {
    started = WiFi.softAP(name.c_str(), nullptr, 1, 0, 4);
    if (!started) {
      Serial.printf("Setup AP start attempt %u failed\n", attempt);
      delay(300);
    }
  }

  if (!started) {
    Serial.println("Setup AP failed after 3 attempts; waiting screen left intact");
    drawFooter();
    return;
  }

  setupApStarted = true;
  startWebServer();
  // Re-issue begin in case the WebServer socket existed on a previous network
  // interface before the Wi-Fi stack was reset.
  server.begin();

  Serial.print("Setup AP: ");
  Serial.println(name);
  Serial.print("Setup IP: ");
  Serial.println(WiFi.softAPIP());
  drawWaitingScreen();
}

bool connectWifi() {
  if (!cfg.ssid.length()) return false;

  // Once the dedicated fallback AP is running, leave it alone. Configuration
  // changes reboot the device, which is the deliberate transition back to STA.
  if (setupApStarted) {
    Serial.println("Setup AP active; suppressing station reconnect attempt");
    return false;
  }

  lastWifiAttemptMs = millis();

  // Start each station attempt from a known radio state. This avoids carrying
  // a timed-out ESP32-S3 association into the next connection attempt.
  WiFi.setAutoReconnect(false);
  WiFi.softAPdisconnect(true);
  WiFi.disconnect(true, false);
  delay(250);

  if (!WiFi.mode(WIFI_STA)) {
    Serial.println("Failed to enter WIFI_STA mode");
    return false;
  }
  delay(100);

  WiFi.setHostname(cfg.hostname.c_str());
  WiFi.setAutoReconnect(true);
  WiFi.begin(cfg.ssid.c_str(), cfg.wifiPassword.c_str());

  Serial.printf("Connecting to Wi-Fi '%s'...\n", cfg.ssid.c_str());
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    if (webStarted) server.handleClient();
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected: ");
    Serial.println(WiFi.localIP());
    configTzTime(cfg.timezoneTz.c_str(), "pool.ntp.org", "time.nist.gov");
    startWebServer();
    server.begin();
    drawFooter();
    return true;
  }

  wl_status_t status = WiFi.status();
  Serial.printf("Wi-Fi connection timed out: %s (%d)\n",
                wifiStatusLabel(status), (int)status);

  // Power the failed STA interface down before the caller enters failsafe AP
  // mode. This also prevents background auto-reconnect from fighting the AP.
  WiFi.setAutoReconnect(false);
  WiFi.disconnect(true, false);
  delay(100);
  return false;
}
