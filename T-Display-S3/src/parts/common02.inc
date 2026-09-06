bool fetchAmbientDevices(DynamicJsonDocument &doc, String &errorOut) {
  errorOut = "";
  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!apiConfigured()) {
    errorOut = "Ambient Application Key and API Key are not configured";
    return false;
  }

  String url = String(AMBIENT_DEVICES_URL)
             + "?apiKey=" + urlEncode(cfg.apiKey)
             + "&applicationKey=" + urlEncode(cfg.applicationKey);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(10);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(12000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/4.0");

  respectAmbientRateLimit();

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize HTTPS request";
    return false;
  }

  int code = http.GET();
  lastAmbientRequestMs = millis();
  lastHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Ambient HTTP " + String(code);
    if (body.length()) errorOut += ": " + body;
    http.end();
    return false;
  }

  DeserializationError err = deserializeJson(doc, http.getStream());
  http.end();
  if (err) {
    errorOut = "JSON parse error: " + String(err.c_str());
    return false;
  }
  if (!doc.is<JsonArray>()) {
    errorOut = "Ambient returned an unexpected JSON structure";
    return false;
  }
  if (doc.size() == 0) {
    errorOut = "Ambient account returned no devices";
    return false;
  }
  return true;
}

bool applySelectedDevice(JsonArray devices, bool allowAutoSelect, String &errorOut) {
  JsonObject selected;
  String wanted = normalizeMac(cfg.macAddress);

  for (JsonObject device : devices) {
    String mac = normalizeMac(String((const char*)(device["macAddress"] | "")));
    if (wanted.length() > 0 && mac == wanted) {
      selected = device;
      break;
    }
  }

  if (selected.isNull()) {
    if (wanted.length() == 0 && allowAutoSelect && devices.size() > 0) {
      selected = devices[0].as<JsonObject>();
      cfg.macAddress = normalizeMac(String((const char*)(selected["macAddress"] | "")));
      cfg.stationName = String((const char*)(selected["info"]["name"] | ""));
      saveConfig();
    } else {
      errorOut = "Configured station MAC was not found";
      return false;
    }
  }

  JsonObject last = selected["lastData"].as<JsonObject>();
  if (last.isNull()) {
    errorOut = "Selected station has no lastData";
    return false;
  }

  float temp = tryField(last, "tempf");
  float humidity = tryField(last, "humidity");
  if (!isfinite(temp) || !isfinite(humidity) || humidity < 0 || humidity > 100) {
    errorOut = "Selected station returned invalid tempf/humidity";
    return false;
  }

  wx.tempF = temp;
  wx.humidity = humidity;
  wx.heatIndexF = nwsHeatIndexF(wx.tempF, wx.humidity);
  wx.dewPointF = tryField(last, "dewPoint", "dewPointf");
  if (!isfinite(wx.dewPointF)) wx.dewPointF = dewPointFromTempHumidityF(wx.tempF, wx.humidity);
  wx.windMph = tryField(last, "windspeedmph");
  wx.gustMph = tryField(last, "windgustmph", "gustmph");
  wx.maxDailyGustMph = tryField(last, "maxdailygust");
  wx.windChillF = nwsWindChillF(wx.tempF, wx.windMph);
  wx.windDirDeg = tryField(last, "winddir");
  wx.dateUtcMs = last["dateutc"] | 0ULL;
  wx.fetchedMs = millis();
  wx.valid = true;

  String foundName = String((const char*)(selected["info"]["name"] | ""));
  if (foundName.length() && foundName != cfg.stationName) {
    cfg.stationName = foundName;
    saveConfig();
  }
  return true;
}


static bool sameLocalDay(uint64_t aMs, uint64_t bMs) {
  if (aMs == 0 || bMs == 0) return false;

  time_t a = (time_t)(aMs / 1000ULL);
  time_t b = (time_t)(bMs / 1000ULL);

  struct tm ta;
  struct tm tb;
  localtime_r(&a, &ta);
  localtime_r(&b, &tb);

  return ta.tm_year == tb.tm_year && ta.tm_yday == tb.tm_yday;
}

static void respectAmbientRateLimit() {
  if (lastAmbientRequestMs == 0) return;

  unsigned long elapsed = millis() - lastAmbientRequestMs;
  if (elapsed < 1100UL) {
    unsigned long waitMs = 1100UL - elapsed;
    while (waitMs > 0) {
      unsigned long slice = waitMs > 50UL ? 50UL : waitMs;
      delay(slice);
      if (webStarted) server.handleClient();
      waitMs -= slice;
    }
  }
}

bool fetchAmbientSummary(String &errorOut) {
  errorOut = "";

  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!apiConfigured() || !cfg.macAddress.length()) {
    errorOut = "Ambient credentials/station are not configured";
    return false;
  }
  if (!wx.valid || wx.dateUtcMs == 0) {
    errorOut = "Current observation is not available";
    return false;
  }

  String url = String(AMBIENT_DEVICES_URL) + "/" + cfg.macAddress
             + "?apiKey=" + urlEncode(cfg.apiKey)
             + "&applicationKey=" + urlEncode(cfg.applicationKey)
             + "&limit=288";

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(12);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(15000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/4.0");

  respectAmbientRateLimit();

  if (!http.begin(client, url)) {
    errorOut = "Unable to initialize Ambient history HTTPS request";
    return false;
  }

  int code = http.GET();
  lastAmbientRequestMs = millis();
  lastSummaryHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = "Ambient history HTTP " + String(code);
    if (body.length()) {
      errorOut += ": ";
      errorOut += body;
    }
    http.end();
    return false;
  }

  // Only retain the two fields needed for the mockup summary. This keeps the
  // memory footprint small even when Ambient returns 288 observations.
  StaticJsonDocument<96> filter;
  filter[0]["dateutc"] = true;
  filter[0]["tempf"] = true;

  DynamicJsonDocument doc(18432);
  DeserializationError jsonErr = deserializeJson(
    doc,
    http.getStream(),
    DeserializationOption::Filter(filter)
  );
  http.end();

  if (jsonErr) {
    errorOut = "Ambient history JSON error: " + String(jsonErr.c_str());
    return false;
  }
  if (!doc.is<JsonArray>() || doc.size() == 0) {
    errorOut = "Ambient history returned no observations";
    return false;
  }

  float high = wx.tempF;
  float low = wx.tempF;
  float yesterday = NAN;

  const uint64_t targetYesterdayMs =
    wx.dateUtcMs > 86400000ULL ? wx.dateUtcMs - 86400000ULL : 0ULL;

  uint64_t bestYesterdayDifference = UINT64_MAX;

  for (JsonObject point : doc.as<JsonArray>()) {
    uint64_t pointMs = point["dateutc"] | 0ULL;
    float pointTemp = tryField(point, "tempf");

    if (pointMs == 0 || !isfinite(pointTemp)) continue;

    if (sameLocalDay(pointMs, wx.dateUtcMs)) {
      if (!isfinite(high) || pointTemp > high) high = pointTemp;
      if (!isfinite(low) || pointTemp < low) low = pointTemp;
    }

    if (targetYesterdayMs > 0) {
      uint64_t delta = pointMs > targetYesterdayMs
                     ? pointMs - targetYesterdayMs
                     : targetYesterdayMs - pointMs;

      if (delta < bestYesterdayDifference) {
        bestYesterdayDifference = delta;
        yesterday = pointTemp;
      }
    }
  }

  wx.todayHighF = high;
  wx.todayLowF = low;
  wx.yesterdayTempF = yesterday;
  wx.fromYesterdayF = isfinite(yesterday) ? wx.tempF - yesterday : NAN;
  wx.summaryValid = isfinite(wx.todayHighF) && isfinite(wx.todayLowF);
  wx.summaryFetchedMs = millis();

  return true;
}


bool pollAmbient(bool forceRedraw = true) {
  WeatherData before = wx;
  String stationNameBefore = cfg.stationName;

  DynamicJsonDocument doc(24576);
  String error;

  if (!fetchAmbientDevices(doc, error)) {
    lastApiError = error;
    Serial.println("Ambient poll failed: " + error);
    if (forceRedraw) {
      lastFooterStateKey = "";
      drawFooter();
    }
    return false;
  }

  if (!applySelectedDevice(doc.as<JsonArray>(), true, error)) {
    lastApiError = error;
    Serial.println("Ambient selection failed: " + error);
    if (forceRedraw) {
      lastFooterStateKey = "";
      drawFooter();
    }
    return false;
  }

  lastApiError = "";
  lastPollMs = millis();

  // The mockup shows "From Yesterday" and today's high/low. Ambient's
  // historical endpoint is refreshed less frequently than current data.
  const unsigned long SUMMARY_REFRESH_MS = 300000UL;
  if (lastSummaryPollMs == 0 ||
      millis() - lastSummaryPollMs >= SUMMARY_REFRESH_MS) {
    String summaryError;
    if (fetchAmbientSummary(summaryError)) {
      lastSummaryError = "";
      lastSummaryPollMs = millis();
    } else {
      lastSummaryError = summaryError;
      Serial.println("Ambient summary failed: " + summaryError);
      // Keep the last successful summary on screen.
      lastSummaryPollMs = millis();
    }
  }

  Serial.printf(
    "Ambient: %s temp=%.2fF rh=%.1f%% hi=%.2fF wc=%.2fF dew=%.2fF wind=%.2f gust=%.2f dir=%.1f mode=%s\n",
    cfg.macAddress.c_str(), wx.tempF, wx.humidity, wx.heatIndexF,
    wx.windChillF, wx.dewPointF, wx.windMph, wx.gustMph,
    wx.windDirDeg, apparentTitle()
  );

  bool changed = weatherDisplayChanged(before, wx) ||
                 stationNameBefore != cfg.stationName;

  if (forceRedraw) {
    if (changed) {
      unsigned long drawStart = millis();
      drawWeatherScreen();
      unsigned long drawMs = millis() - drawStart;
      Serial.printf("Display redraw: %lu ms\n", drawMs);
      lastFooterStateKey = footerStateKey();
    } else {
      String newKey = footerStateKey();
      if (newKey != lastFooterStateKey) {
        lastFooterStateKey = newKey;
        drawFooter();
      }
    }
  }

  return true;
}

