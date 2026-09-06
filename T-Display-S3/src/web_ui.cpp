#include <WiFi.h>
#include <ArduinoJson.h>
#include "app_state.h"
#include "web_ui.h"
#include "ambient_weather.h"
#include "config_store.h"
#include "display_ui.h"
#include "time_utils.h"
#include "weather_math.h"
#include "wifi_manager.h"

String htmlEscape(const String &in) {
  String out;
  out.reserve(in.length() + 16);
  for (size_t i = 0; i < in.length(); i++) {
    char c = in[i];
    switch (c) {
      case '&': out += F("&amp;"); break;
      case '<': out += F("&lt;"); break;
      case '>': out += F("&gt;"); break;
      case '"': out += F("&quot;"); break;
      case '\'': out += F("&#39;"); break;
      default: out += c; break;
    }
  }
  return out;
}

String pageHead(const String &title) {
  String h;
  h.reserve(1800);
  h += F("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>");
  h += htmlEscape(title);
  h += F("</title><style>");
  h += F("body{font-family:system-ui,-apple-system,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:18px}");
  h += F(".wrap{max-width:760px;margin:auto}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:18px;margin:14px 0}");
  h += F("h1,h2{margin-top:0}.big{font-size:4rem;font-weight:800;line-height:1}.muted{color:#8b949e}");
  h += F("label{display:block;font-weight:650;margin-top:14px}input{box-sizing:border-box;width:100%;padding:11px;margin-top:5px;background:#0d1117;color:#e6edf3;border:1px solid #484f58;border-radius:8px}");
  h += F("button,.btn{display:inline-block;background:#238636;color:white;border:0;border-radius:8px;padding:10px 14px;text-decoration:none;font-weight:650;cursor:pointer;margin:6px 6px 6px 0}");
  h += F(".secondary{background:#30363d}.danger{background:#b62324}.ok{color:#3fb950}.bad{color:#f85149}code{background:#21262d;padding:2px 5px;border-radius:4px}");
  h += F("table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #30363d;text-align:left}");
  h += F("</style></head><body><div class='wrap'>");
  return h;
}

String pageTail() { return F("</div></body></html>"); }

void handleRoot() {
  String html = pageHead("Apparent Temperature Display");
  html += F("<h1>Apparent Temperature Display</h1><div class='card'>");

  if (wx.valid) {
    html += F("<div class='big'>");
    html += String(apparentOutdoorF(), 1);
    html += F("&deg;F</div>");

    html += F("<p><b>");
    html += apparentTitle();
    html += F("</b> &mdash; <b>");
    html += apparentRiskLabel();
    html += F("</b><br>");

    html += F("Temperature: <b>");
    html += String(wx.tempF, 1);
    html += F("&deg;F</b><br>");

    html += F("Humidity: <b>");
    html += String(wx.humidity, 0);
    html += F("%</b><br>");

    if (isfinite(wx.dewPointF)) {
      html += F("Dew point: <b>");
      html += String(wx.dewPointF, 1);
      html += F("&deg;F</b><br>");
    }

    if (isfinite(wx.windMph)) {
      html += F("Wind: <b>");
      html += String(wx.windMph, 1);
      html += F(" mph</b><br>");
    }

    if (isfinite(wx.fromYesterdayF)) {
      html += F("From yesterday: <b>");
      if (wx.fromYesterdayF >= 0.0f) html += "+";
      html += String(wx.fromYesterdayF, 1);
      html += F("&deg;F</b><br>");
    }

    if (wx.summaryValid) {
      html += F("Today's high / low: <b>");
      html += String(wx.todayHighF, 1);
      html += F("&deg;F / ");
      html += String(wx.todayLowF, 1);
      html += F("&deg;F</b><br>");
    }

    html += F("Observation age: <b>");
    html += String(observationAgeSeconds());
    html += F(" sec</b>");

    if (dataStale()) {
      html += F(" <span class='bad'>(STALE)</span>");
    }
    html += F("</p>");
  } else {
    html += F("<p class='muted'>");
    if (lastApiError.length()) {
      html += htmlEscape(lastApiError);
    } else {
      html += F("Waiting for the first successful AmbientWeather.net poll.");
    }
    html += F("</p>");
  }

  html += F("</div><div class='card'><h2>Status</h2><table>");

  html += F("<tr><th>Wi-Fi</th><td>");
  html += (WiFi.status() == WL_CONNECTED) ? "Connected" : "Not connected";
  html += F("</td></tr>");

  html += F("<tr><th>IP</th><td>");
  html += htmlEscape(currentIp());
  html += F("</td></tr>");

  html += F("<tr><th>Station</th><td>");
  html += htmlEscape(cfg.stationName.length() ? cfg.stationName : String("(auto)"));
  html += F("</td></tr>");

  html += F("<tr><th>MAC</th><td>");
  html += htmlEscape(cfg.macAddress.length() ? cfg.macAddress : String("(auto)"));
  html += F("</td></tr>");

  html += F("<tr><th>Timezone</th><td><code>");
  html += htmlEscape(cfg.timezoneTz);
  html += F("</code></td></tr>");

  html += F("<tr><th>Poll interval</th><td>");
  html += String(cfg.pollSeconds);
  html += F(" sec</td></tr>");

  html += F("<tr><th>Ambient API</th><td>");
  html += apiConfigured() ? "Configured" : "Not configured";
  html += F("</td></tr>");

  if (lastHttpCode) {
    html += F("<tr><th>Last HTTP code</th><td>");
    html += String(lastHttpCode);
    html += F("</td></tr>");
  }

  if (lastSummaryHttpCode) {
    html += F("<tr><th>History HTTP code</th><td>");
    html += String(lastSummaryHttpCode);
    html += F("</td></tr>");
  }
  if (lastSummaryError.length()) {
    html += F("<tr><th>History warning</th><td class='bad'>");
    html += htmlEscape(lastSummaryError);
    html += F("</td></tr>");
  }

  if (lastApiError.length()) {
    html += F("<tr><th>Last API error</th><td class='bad'>");
    html += htmlEscape(lastApiError);
    html += F("</td></tr>");
  }

  html += F("</table></div>");
  html += F("<a class='btn' href='/config'>Configuration</a>");
  html += F("<a class='btn secondary' href='/discover'>Discover stations</a>");
  html += F("<a class='btn secondary' href='/poll'>Poll now</a>");
  html += F("<a class='btn secondary' href='/status'>JSON</a>");
  html += pageTail();

  server.send(200, "text/html", html);
}

void handleConfig() {
  String html = pageHead("Configuration");
  html += F("<h1>Configuration</h1>");
  html += F("<div class='card'><b>Persistent settings:</b> values saved here override any compile-time first-boot defaults and remain active across reboots. Factory Reset clears them and allows the compiled defaults to seed again.</div>");

  if (setupApStarted) {
    html += F("<div class='card'><b>Setup access point active.</b><br>");
    html += F("Connect to the ESP32 setup network, enter Wi-Fi and Ambient settings below, save, and the device will reboot.</div>");
  }

  html += F("<form method='post' action='/save'>");
  html += F("<div class='card'><h2>Wi-Fi</h2>");

  html += F("<label>Wi-Fi SSID<input name='ssid' maxlength='32' value='");
  html += htmlEscape(cfg.ssid);
  html += F("' required></label>");

  html += F("<label>Wi-Fi password<input type='password' name='wpass' maxlength='64' placeholder='Leave blank to keep saved password'></label>");

  html += F("<label>Hostname<input name='host' maxlength='32' value='");
  html += htmlEscape(cfg.hostname);
  html += F("'></label>");

  html += F("<label>Timezone (POSIX TZ string)<input name='tz' maxlength='96' value='");
  html += htmlEscape(cfg.timezoneTz);
  html += F("'></label>");
  html += F("</div>");

  html += F("<div class='card'><h2>AmbientWeather.net</h2>");
  html += F("<p class='muted'>Ambient requires both an Application Key and an API Key. Saved secrets are never rendered back into the page.</p>");

  html += F("<label>Application Key<input type='password' name='appkey' maxlength='128' placeholder='");
  if (cfg.applicationKey.length()) {
    html += F("Saved — leave blank to keep");
  } else {
    html += F("Enter applicationKey");
  }
  html += F("'></label>");

  html += F("<label>API Key / Device Key<input type='password' name='apikey' maxlength='128' placeholder='");
  if (cfg.apiKey.length()) {
    html += F("Saved — leave blank to keep");
  } else {
    html += F("Enter apiKey");
  }
  html += F("'></label>");

  html += F("<label>Station MAC address<input name='mac' maxlength='32' value='");
  html += htmlEscape(cfg.macAddress);
  html += F("' placeholder='Leave blank to auto-select first station'></label>");

  html += F("<label>Poll interval (seconds)<input type='number' min='");
  html += String(MIN_POLL_SECONDS);
  html += F("' max='3600' name='poll' value='");
  html += String(cfg.pollSeconds);
  html += F("'></label>");

  html += F("<label>Mark data stale after (seconds)<input type='number' min='");
  html += String(MIN_STALE_SECONDS);
  html += F("' max='86400' name='stale' value='");
  html += String(cfg.staleSeconds);
  html += F("'></label>");

  html += F("</div><button type='submit'>Save &amp; reboot</button>");
  html += F("<a class='btn secondary' href='/'>Cancel</a></form>");

  html += F("<div class='card'><h2>Credential management</h2>");
  html += F("<form method='post' action='/clear-ambient' onsubmit=\"return confirm('Clear saved Ambient credentials and station selection?')\">");
  html += F("<button class='danger' type='submit'>Clear Ambient credentials</button></form>");
  html += F("<form method='post' action='/factory-reset' onsubmit=\"return confirm('Erase all settings including Wi-Fi?')\">");
  html += F("<button class='danger' type='submit'>Factory reset</button></form>");
  html += F("</div>");

  html += pageTail();
  server.send(200, "text/html", html);
}

void handleSave() {
  if (server.hasArg("ssid")) cfg.ssid = server.arg("ssid");
  if (server.hasArg("wpass") && server.arg("wpass").length()) cfg.wifiPassword = server.arg("wpass");
  if (server.hasArg("host")) {
    String h = server.arg("host");
    h.trim();
    if (h.length()) cfg.hostname = h;
  }
  if (server.hasArg("tz")) {
    String tz = server.arg("tz");
    tz.trim();
    if (tz.length()) cfg.timezoneTz = tz;
  }
  if (server.hasArg("appkey") && server.arg("appkey").length()) cfg.applicationKey = server.arg("appkey");
  if (server.hasArg("apikey") && server.arg("apikey").length()) cfg.apiKey = server.arg("apikey");
  if (server.hasArg("mac")) cfg.macAddress = normalizeMac(server.arg("mac"));
  if (server.hasArg("poll")) {
    uint32_t p = (uint32_t)server.arg("poll").toInt();
    if (p < MIN_POLL_SECONDS) p = MIN_POLL_SECONDS;
    if (p > 3600UL) p = 3600UL;
    cfg.pollSeconds = p;
  }
  if (server.hasArg("stale")) {
    uint32_t s = (uint32_t)server.arg("stale").toInt();
    if (s < MIN_STALE_SECONDS) s = MIN_STALE_SECONDS;
    if (s > 86400UL) s = 86400UL;
    cfg.staleSeconds = s;
  }
  cfg.stationName = "";
  saveConfig();

  String html = pageHead("Saved");
  html += F("<div class='card'><h1>Settings saved</h1><p>The device is rebooting.</p></div>");
  html += pageTail();
  server.send(200, "text/html", html);
  delay(900);
  ESP.restart();
}

void handleClearAmbient() {
  cfg.applicationKey = "";
  cfg.apiKey = "";
  cfg.macAddress = "";
  cfg.stationName = "";
  saveConfig();
  server.sendHeader("Location", "/config");
  server.send(303);
}

void handleFactoryReset() {
  prefs.begin("heatidx", false);
  prefs.clear();
  prefs.end();
  String html = pageHead("Factory reset");
  html += F("<div class='card'><h1>Settings erased</h1><p>NVS was cleared. On reboot the compiled first-boot defaults will be seeded again; if no Wi-Fi default is compiled, setup mode will be used.</p></div>");
  html += pageTail();
  server.send(200, "text/html", html);
  delay(900);
  ESP.restart();
}

void handlePollNow() {
  bool ok = pollAmbient(true);

  if (ok) {
    server.sendHeader("Location", "/");
    server.send(303);
  } else {
    String html = pageHead("Poll failed");
    html += F("<div class='card'><h1>Ambient poll failed</h1><p class='bad'>");
    html += htmlEscape(lastApiError);
    html += F("</p><a class='btn secondary' href='/'>Back</a></div>");
    html += pageTail();
    server.send(502, "text/html", html);
  }
}

void handleDiscover() {
  String html = pageHead("Discover stations");
  html += F("<h1>Ambient stations</h1>");

  if (!apiConfigured()) {
    html += F("<div class='card'><p>Configure your Ambient keys first.</p>");
    html += F("<a class='btn' href='/config'>Configuration</a></div>");
    html += pageTail();
    server.send(400, "text/html", html);
    return;
  }

  DynamicJsonDocument doc(24576);
  String error;

  if (!fetchAmbientDevices(doc, error)) {
    lastApiError = error;
    html += F("<div class='card'><p class='bad'>");
    html += htmlEscape(error);
    html += F("</p></div>");
    html += pageTail();
    server.send(502, "text/html", html);
    return;
  }

  html += F("<div class='card'><table>");
  html += F("<tr><th>Name</th><th>Location</th><th>MAC</th><th></th></tr>");

  for (JsonObject device : doc.as<JsonArray>()) {
    String mac = normalizeMac(String((const char*)(device["macAddress"] | "")));
    String name = String((const char*)(device["info"]["name"] | ""));
    String location = String((const char*)(device["info"]["location"] | ""));

    html += F("<tr><td>");
    html += htmlEscape(name);
    html += F("</td><td>");
    html += htmlEscape(location);
    html += F("</td><td><code>");
    html += htmlEscape(mac);
    html += F("</code></td><td>");

    html += F("<form method='post' action='/select' style='margin:0'>");
    html += F("<input type='hidden' name='mac' value='");
    html += htmlEscape(mac);
    html += F("'>");
    html += F("<input type='hidden' name='name' value='");
    html += htmlEscape(name);
    html += F("'>");
    html += F("<button type='submit'>Select</button></form>");
    html += F("</td></tr>");
  }

  html += F("</table></div>");
  html += F("<a class='btn secondary' href='/'>Back</a>");
  html += pageTail();
  server.send(200, "text/html", html);
}

void handleSelect() {
  if (!server.hasArg("mac")) {
    server.send(400, "text/plain", "Missing station MAC");
    return;
  }
  cfg.macAddress = normalizeMac(server.arg("mac"));
  cfg.stationName = server.hasArg("name") ? server.arg("name") : "";
  saveConfig();
  lastPollMs = 0;
  lastSummaryPollMs = 0;
  wx.summaryValid = false;
  wx.yesterdayTempF = NAN;
  wx.fromYesterdayF = NAN;
  wx.todayHighF = NAN;
  wx.todayLowF = NAN;
  pollAmbient(true);
  server.sendHeader("Location", "/");
  server.send(303);
}

String jsonStatus() {
  String s;
  s.reserve(900);
  s += "{";
  s += "\"wifi_connected\":";
  s += (WiFi.status() == WL_CONNECTED ? "true" : "false");
  s += ",\"setup_ap\":";
  s += (setupApStarted ? "true" : "false");
  s += ",\"ip\":\"" + currentIp() + "\"";
  s += ",\"api_configured\":";
  s += (apiConfigured() ? "true" : "false");
  s += ",\"station_mac\":\"" + cfg.macAddress + "\"";
  s += ",\"station_name\":\"" + cfg.stationName + "\"";
  s += ",\"poll_seconds\":" + String(cfg.pollSeconds);
  s += ",\"stale_seconds\":" + String(cfg.staleSeconds);
  s += ",\"last_http_code\":" + String(lastHttpCode);
  s += ",\"last_api_error\":\"" + lastApiError + "\"";
  s += ",\"valid\":";
  s += (wx.valid ? "true" : "false");
  if (wx.valid) {
    s += ",\"tempf\":" + String(wx.tempF, 2);
    s += ",\"humidity\":" + String(wx.humidity, 1);
    s += ",\"heat_index_f\":";
    s += String(wx.heatIndexF, 2);
    s += ",\"wind_chill_f\":";
    s += String(wx.windChillF, 2);
    s += ",\"apparent_f\":";
    s += String(apparentOutdoorF(), 2);
    s += ",\"mode\":\"";
    s += apparentTitle();
    s += "\"";
    s += ",\"dew_point_f\":";
    s += String(wx.dewPointF, 2);
    s += ",\"wind_mph\":" + String(wx.windMph, 2);
    s += ",\"gust_mph\":" + String(wx.gustMph, 2);
    s += ",\"maxdailygust_mph\":" + String(wx.maxDailyGustMph, 2);
    s += ",\"wind_dir_deg\":" + String(wx.windDirDeg, 1);
    if (isfinite(wx.yesterdayTempF)) {
      s += ",\"yesterday_temp_f\":" + String(wx.yesterdayTempF, 2);
    }
    if (isfinite(wx.fromYesterdayF)) {
      s += ",\"from_yesterday_f\":" + String(wx.fromYesterdayF, 2);
    }
    if (wx.summaryValid) {
      s += ",\"today_high_f\":" + String(wx.todayHighF, 2);
      s += ",\"today_low_f\":" + String(wx.todayLowF, 2);
    }
    s += ",\"observation_age_seconds\":" + String(observationAgeSeconds());
    s += ",\"stale\":";
    s += (dataStale() ? "true" : "false");
  }
  s += "}";
  return s;
}

void startWebServer() {
  if (webStarted) return;
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, [](){ server.send(200, "application/json", jsonStatus()); });
  server.on("/config", HTTP_GET, handleConfig);
  server.on("/save", HTTP_POST, handleSave);
  server.on("/discover", HTTP_GET, handleDiscover);
  server.on("/select", HTTP_POST, handleSelect);
  server.on("/poll", HTTP_GET, handlePollNow);
  server.on("/clear-ambient", HTTP_POST, handleClearAmbient);
  server.on("/factory-reset", HTTP_POST, handleFactoryReset);
  server.onNotFound([](){ server.send(404, "text/plain", "Not found"); });
  server.begin();
  webStarted = true;
  Serial.println("Web UI started on port 80");
}
