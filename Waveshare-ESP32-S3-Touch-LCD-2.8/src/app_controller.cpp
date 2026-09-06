#include <WiFi.h>
#include "app_state.h"
#include "app_controller.h"
#include "ambient_weather.h"
#include "config_store.h"
#include "display_ui.h"
#include "ui_state.h"
#include "web_ui.h"
#include "wifi_manager.h"
#include "config.h"

void appSetup() {
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

void appLoop() {
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
