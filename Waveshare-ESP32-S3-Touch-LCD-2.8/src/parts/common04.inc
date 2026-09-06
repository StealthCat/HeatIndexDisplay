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
