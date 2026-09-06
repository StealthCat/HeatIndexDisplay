#include <WiFi.h>
#include <time.h>
#include "app_state.h"
#include "wifi_manager.h"
#include "config.h"
#include "display_ui.h"
#include "web_ui.h"

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
