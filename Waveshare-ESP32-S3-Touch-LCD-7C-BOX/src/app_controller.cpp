#include <WiFi.h>
#include "app_state.h"
#include "app_controller.h"
#include "config_store.h"
#include "display_ui.h"
#include "forecast_weather.h"
#include "ui_state.h"
#include "web_ui.h"
#include "weather_source.h"
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
    lastApiError = "Configure ";
    lastApiError += weatherSourceLabel();
    lastApiError += " credentials at /config";
    drawWaitingScreen();
    return;
  }
  pollWeatherSource(true);
  pollForecastIfDue(true);
}

void appLoop() {
  static bool forecastPhaseInitialized = false;
  static bool lastForecastTomorrow = false;
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
      pollWeatherSource(true);
    }
  }

  if (nowMs - lastUiStateCheckMs >= 1000UL) {
    lastUiStateCheckMs = nowMs;

    if (WiFi.status() == WL_CONNECTED && wx.valid) {
      pollForecastIfDue(true);
    }

    if (wx.forecastValid) {
      bool showTomorrow = forecastShowsTomorrow();
      if (!forecastPhaseInitialized || showTomorrow != lastForecastTomorrow) {
        lastForecastTomorrow = showTomorrow;
        forecastPhaseInitialized = true;
        drawForecastHighLowCard();
      }
    } else {
      forecastPhaseInitialized = false;
    }

    String newKey = footerStateKey();
    if (newKey != lastFooterStateKey) {
      lastFooterStateKey = newKey;
      drawFooter();
    }
  }

  delay(20);
}
