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

  // A failed STA association can still be active when we enter fallback
  // setup mode. Stop only the STA attempt (do not erase credentials), then
  // give the ESP32 Wi-Fi stack a moment to settle before enabling AP+STA.
  WiFi.disconnect(false, false);
  delay(100);

  if (!WiFi.mode(WIFI_AP_STA)) {
    Serial.println("Failed to enter WIFI_AP_STA mode for setup AP");
    startWebServer();
    // The waiting screen is already present. Updating only the footer avoids
    // a full-screen black flash if the radio transition itself fails.
    drawFooter();
    return;
  }
  delay(100);

  String name = setupApName();
  bool started = false;
  for (uint8_t attempt = 1; attempt <= 3 && !started; ++attempt) {
    started = WiFi.softAP(name.c_str());
    if (!started) {
      Serial.printf("Setup AP start attempt %u failed\n", attempt);
      delay(250);
    }
  }

  startWebServer();

  if (!started) {
    Serial.println("Setup AP failed after 3 attempts; leaving waiting screen intact");
    // Do not call drawWaitingScreen() here. The retry loop may reach this
    // path repeatedly, and clearing/repainting the whole TFT caused the
    // visible black flashing reported on the T-Display S3.
    drawFooter();
    return;
  }

  setupApStarted = true;
  Serial.print("Setup AP: ");
  Serial.println(name);
  Serial.print("Setup IP: ");
  Serial.println(WiFi.softAPIP());
  drawWaitingScreen();
}

bool connectWifi() {
  if (!cfg.ssid.length()) return false;

  // Record the attempt here as well as in appLoop so the initial boot failure
  // does not immediately launch a second 20-second association attempt.
  lastWifiAttemptMs = millis();

  // Clear any stale/pending station association without touching the setup AP
  // or erasing saved credentials. This is especially important after a timed
  // out connection attempt on Arduino-ESP32 2.x used by the T-Display build.
  WiFi.disconnect(false, false);
  delay(100);

  if (!WiFi.mode(setupApStarted ? WIFI_AP_STA : WIFI_STA)) {
    Serial.println("Failed to set Wi-Fi mode before station connection");
    return false;
  }

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

    const bool wasSetupAp = setupApStarted;
    if (setupApStarted) {
      WiFi.softAPdisconnect(true);
      setupApStarted = false;
      WiFi.mode(WIFI_STA);
    }

    // On an ordinary reconnect the middle waiting card is already on screen,
    // so only the footer needs refreshing. If we are leaving setup mode, a
    // one-time full redraw is appropriate to replace SETUP with WAITING.
    if (wasSetupAp) drawWaitingScreen();
    else drawFooter();
    return true;
  }

  wl_status_t status = WiFi.status();
  Serial.printf("Wi-Fi connection timed out: %s (%d)\n",
                wifiStatusLabel(status), (int)status);
  return false;
}
