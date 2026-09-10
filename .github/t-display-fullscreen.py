from pathlib import Path
import re

header = Path('T-Display-S3/include/display_ui.h')
header.write_text('''#pragma once

void displayBegin();
void drawWaitingScreen();
void drawWeatherScreen();
void drawFooter();
void drawForecastHighLowCard();
void toggleDisplayPage();
bool displayDetailPageActive();
''')

main = Path('T-Display-S3/src/main.cpp')
main.write_text('''#include <Arduino.h>
#include <esp_system.h>
#include "app_controller.h"
#include "app_state.h"
#include "display_ui.h"
#include "ui_state.h"

namespace {
constexpr uint8_t BUTTON_BOOT_PIN = 0;
constexpr uint8_t BUTTON_USER_PIN = 14;
constexpr unsigned long BUTTON_DEBOUNCE_MS = 180UL;

bool lastBootButton = HIGH;
bool lastUserButton = HIGH;
unsigned long lastButtonToggleMs = 0;

void setupDisplayButtons() {
  pinMode(BUTTON_BOOT_PIN, INPUT_PULLUP);
  pinMode(BUTTON_USER_PIN, INPUT_PULLUP);
  lastBootButton = digitalRead(BUTTON_BOOT_PIN);
  lastUserButton = digitalRead(BUTTON_USER_PIN);
}

void handleDisplayButtons() {
  const bool bootButton = digitalRead(BUTTON_BOOT_PIN);
  const bool userButton = digitalRead(BUTTON_USER_PIN);
  const bool pressed = (lastBootButton == HIGH && bootButton == LOW) ||
                       (lastUserButton == HIGH && userButton == LOW);
  const unsigned long nowMs = millis();

  if (pressed && nowMs - lastButtonToggleMs >= BUTTON_DEBOUNCE_MS) {
    lastButtonToggleMs = nowMs;
    toggleDisplayPage();
  }

  lastBootButton = bootButton;
  lastUserButton = userButton;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(250);
  Serial.printf("\\nHeatIndexDisplay boot: reset_reason=%d free_heap=%u free_psram=%u\\n",
                (int)esp_reset_reason(), ESP.getFreeHeap(), ESP.getFreePsram());

  setupDisplayButtons();
  displayBegin();
  drawWaitingScreen();
  appSetup();
  lastFooterStateKey = footerStateKey();
}

void loop() {
  handleDisplayButtons();
  appLoop();
}
''')

path = Path('T-Display-S3/src/display_ui.cpp')
text = path.read_text()

marker = 'static const uint16_t C_WHITE = 0xFFFF;\n'
assert marker in text
text = text.replace(marker, marker + '''
// The t-display branch uses two runtime pages. The full-screen apparent
// temperature page is the default; either physical button toggles details.
static bool detailsPageActive = false;
static bool waitingScreenActive = true;
''', 1)

forecast_block = r'void drawForecastHighLowCard\(\) \{.*?\n\}\n\nvoid drawHeader\(\)'
forecast_repl = r'''static void drawDetailMetricCard(int x, int y, int w, int h,
                                 const String &label, const String &value) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 8, false);

  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.72f);
  drawBoldText(label, x + w / 2, y + 11, cyan);
  display.setTextSize(1.0f);

  if (value.length() > 7) {
    display.setFont(&fonts::Font2);
  } else {
    display.setFont(&fonts::Font4);
  }
  drawBoldText(value, x + w / 2, y + 34, C_WHITE);
}

void drawForecastHighLowCard() {
  if (waitingScreenActive || !detailsPageActive || !wx.valid) return;

  const uint16_t muted = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();
  drawConceptCard(6, 212, 158, 48, 8, true);

  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.72f);
  drawBoldText(tomorrow ? "TOMORROW HIGH / LOW" : "TODAY HIGH / LOW", 85, 224, muted);
  display.setTextSize(1.0f);

  String hl = "-- / --";
  if (wx.forecastValid) {
    const float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    const float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high) && isfinite(low)) {
      hl = String((int)lroundf(high)) + String("\\xB0") + " / " +
           String((int)lroundf(low)) + String("\\xB0");
    }
  }

  display.setFont(&fonts::Font4);
  drawBoldText(hl, 85, 244, C_WHITE);
}

void drawHeader()'''
text, count = re.subn(forecast_block, forecast_repl, text, count=1, flags=re.S)
assert count == 1, 'forecast block replacement failed'

footer_block = r'void drawFooter\(\) \{.*?\n\}\n\n\nvoid drawWaitingScreen\(\)'
footer_repl = r'''static void drawHeroStatusCard() {
  const uint16_t muted = rgb565(191, 215, 229);
  const uint16_t green = rgb565(117, 237, 79);
  const uint16_t red = rgb565(255, 122, 103);

  drawConceptCard(7, 269, 156, 44, 9, true);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.68f);

  String line1;
  String line2;
  uint16_t stateColor = green;
  if (WiFi.status() != WL_CONNECTED) {
    line1 = setupApStarted ? "SETUP 192.168.4.1" : "WI-FI DISCONNECTED";
    line2 = "OFFLINE";
    stateColor = red;
  } else if (!apiConfigured()) {
    line1 = "API SETUP NEEDED";
    line2 = "OFFLINE";
    stateColor = red;
  } else {
    line1 = "UPDATED " + updateClockText();
    line2 = dataStale() ? "STALE" : "ONLINE";
    stateColor = dataStale() ? red : green;
  }

  display.setTextColor(C_WHITE);
  display.drawString(line1, 85, 279);
  drawBoldText(line2, 85, 292, stateColor);
  display.setTextSize(0.58f);
  display.setTextColor(muted);
  display.drawString("EITHER BUTTON: DETAILS", 85, 305);
  display.setTextSize(1.0f);
}

static void drawDetailsStatusCard() {
  const uint16_t muted = rgb565(168, 198, 216);
  const uint16_t green = rgb565(117, 237, 79);
  const uint16_t red = rgb565(255, 122, 103);

  drawConceptCard(6, 264, 158, 50, 8, true);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.66f);

  String line1;
  String state;
  uint16_t stateColor = green;
  if (WiFi.status() != WL_CONNECTED) {
    line1 = "WI-FI DISCONNECTED";
    state = "OFFLINE";
    stateColor = red;
  } else if (!apiConfigured()) {
    line1 = "API SETUP NEEDED";
    state = "OFFLINE";
    stateColor = red;
  } else {
    line1 = "UPDATED " + updateClockText();
    state = dataStale() ? "STALE" : "ONLINE";
    stateColor = dataStale() ? red : green;
  }

  display.setTextColor(C_WHITE);
  display.drawString(line1, 85, 276);
  drawBoldText(state, 85, 290, stateColor);
  display.setTextSize(0.56f);
  display.setTextColor(muted);
  display.drawString("EITHER BUTTON: HEAT INDEX", 85, 305);
  display.setTextSize(1.0f);
}

void drawFooter() {
  if (!waitingScreenActive && wx.valid) {
    if (detailsPageActive) drawDetailsStatusCard();
    else drawHeroStatusCard();
    return;
  }

  const uint16_t muted = rgb565(168, 198, 216);
  const uint16_t green = rgb565(117, 237, 79);
  const uint16_t red = rgb565(255, 122, 103);

  display.fillRect(0, 289, 170, 31, C_BLACK);
  drawConceptCard(7, 292, 156, 23, 7, true);

  display.setTextSize(1.0f);
  display.setFont(&fonts::Font0);

  if (WiFi.status() != WL_CONNECTED) {
    display.setTextDatum(textdatum_t::middle_center);
    display.setTextColor(C_WHITE);
    display.drawString(setupApStarted ? "Setup 192.168.4.1" : "Wi-Fi disconnected", 85, 304);
    return;
  }
  if (!apiConfigured()) {
    display.setTextDatum(textdatum_t::middle_center);
    display.setTextColor(C_WHITE);
    display.drawString("Open /config", 85, 304);
    return;
  }

  const bool offline = !wx.valid;
  const bool stale = !offline && dataStale();
  const uint16_t stateColor = offline ? red : (stale ? red : green);

  drawClockIcon(18, 304, muted);

  String left;
  String state;
  uint16_t leftColor = C_WHITE;
  if (offline) {
    left = lastApiError.length() ? "Weather API error" : "Fetching weather...";
    state = "OFFLINE";
    leftColor = lastApiError.length() ? red : C_WHITE;
  } else {
    left = "Updated ";
    left += updateClockText();
    state = stale ? "STALE" : "ONLINE";
    leftColor = stale ? red : C_WHITE;
  }

  display.setTextDatum(textdatum_t::middle_left);
  display.setTextSize(0.62f);
  display.setTextColor(leftColor);
  display.drawString(left, 31, 304);

  display.drawFastVLine(119, 297, 13, rgb565(85, 115, 133));
  display.fillCircle(130, 304, 2, stateColor);
  drawBoldText(state, 136, 304, stateColor);
  display.setTextSize(1.0f);
}


void drawWaitingScreen()'''
text, count = re.subn(footer_block, footer_repl, text, count=1, flags=re.S)
assert count == 1, 'footer block replacement failed'

waiting_start = 'void drawWaitingScreen() {\n  display.fillScreen(C_BLACK);'
assert waiting_start in text
text = text.replace(waiting_start, 'void drawWaitingScreen() {\n  waitingScreenActive = true;\n  display.fillScreen(C_BLACK);', 1)

weather_block = r'void drawWeatherScreen\(\) \{.*?\n\}\n\nvoid displayBegin\(\)'
weather_repl = r'''static void drawFullScreenApparentValue(float apparentF) {
  const String value = String((int)lroundf(apparentF));
  const float valueScale = value.length() >= 3 ? 1.0f : 1.20f;

  display.setTextDatum(textdatum_t::middle_left);
  display.setTextColor(C_WHITE);
  display.setFont(&fonts::Font7);
  display.setTextSize(valueScale);
  const int valueWidth = display.textWidth(value);

  display.setFont(&fonts::Font4);
  display.setTextSize(1.0f);
  const int fWidth = display.textWidth("F");
  const int unitGap = 13;
  const int groupWidth = valueWidth + unitGap + fWidth;
  const int startX = (170 - groupWidth) / 2;

  display.setFont(&fonts::Font7);
  display.setTextSize(valueScale);
  display.drawString(value, startX, 150);

  const int degreeX = startX + valueWidth + 4;
  display.drawCircle(degreeX + 2, 132, 3, C_WHITE);
  display.setFont(&fonts::Font4);
  display.setTextSize(1.0f);
  display.drawString("F", degreeX + 8, 151);
}

static void drawFullScreenHero() {
  const float apparentF = apparentOutdoorF();
  const RiskStyle risk = riskFor(apparentF);
  const bool cold = windChillApplies();

  for (int y = 0; y < 320; ++y) {
    const float t = (float)y / 319.0f;
    display.drawFastHLine(0, y, 170, lerp565(risk.panelTop, risk.panelBottom, t));
  }

  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 20) station = station.substring(0, 20);
  display.setTextDatum(textdatum_t::middle_center);
  display.setTextColor(C_WHITE);
  display.setFont(&fonts::Font2);
  drawBoldText(station, 85, 17, C_WHITE);

  display.setFont(&fonts::Font0);
  display.setTextSize(0.68f);
  display.setTextColor(rgb565(222, 235, 243));
  display.drawString(currentDateText(), 85, 36);
  display.setTextSize(1.0f);

  display.setFont(&fonts::Font4);
  drawBoldText(apparentTitle(), 85, 67, C_WHITE);

  if (cold) drawHeroWind(66, 91);
  else drawHeroSun(85, 94);

  drawFullScreenApparentValue(apparentF);

  display.fillRoundRect(14, 207, 142, 38, 19, risk.status);
  display.drawRoundRect(14, 207, 142, 38, 19, risk.accent);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentRiskLabel(), 85, 226, risk.accent);

  drawHeroStatusCard();
}

static void drawDetailsScreen() {
  const uint16_t muted = rgb565(157, 200, 228);
  display.fillScreen(C_BLACK);

  drawConceptCard(6, 6, 158, 34, 8, true);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font2);
  drawBoldText("WEATHER DETAILS", 85, 16, C_WHITE);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.58f);
  display.setTextColor(muted);
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 22) station = station.substring(0, 22);
  display.drawString(station, 85, 31);
  display.setTextSize(1.0f);

  const String temp = isfinite(wx.tempF) ? String(wx.tempF, 1) + String("\\xB0") + "F" : "--";
  const String humidity = isfinite(wx.humidity) ? String((int)lroundf(wx.humidity)) + "%" : "--";
  const String dew = isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String("\\xB0") + "F" : "--";
  const String delta = signedTempDelta(wx.fromYesterdayF);

  String wind = isfinite(wx.windMph) ? String(wx.windMph, 1) : "--";
  wind += " / ";
  wind += isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--";

  String direction = "--";
  if (isfinite(wx.windDirDeg)) {
    direction = String((int)lroundf(wx.windDirDeg)) + String("\\xB0") + " " + directionText(wx.windDirDeg);
  }

  drawDetailMetricCard(6, 44, 78, 52, "TEMPERATURE", temp);
  drawDetailMetricCard(87, 44, 77, 52, "HUMIDITY", humidity);
  drawDetailMetricCard(6, 100, 78, 52, "DEW POINT", dew);
  drawDetailMetricCard(87, 100, 77, 52, "VS YDAY", delta);
  drawDetailMetricCard(6, 156, 78, 52, "WIND / GUST", wind);
  drawDetailMetricCard(87, 156, 77, 52, "DIRECTION", direction);

  drawForecastHighLowCard();
  drawDetailsStatusCard();
}

void drawWeatherScreen() {
  if (!wx.valid) {
    drawWaitingScreen();
    return;
  }

  waitingScreenActive = false;
  if (detailsPageActive) drawDetailsScreen();
  else drawFullScreenHero();
}

void toggleDisplayPage() {
  if (!wx.valid || waitingScreenActive) return;
  detailsPageActive = !detailsPageActive;
  Serial.printf("T-Display page: %s\\n", detailsPageActive ? "details" : "heat-index");
  drawWeatherScreen();
}

bool displayDetailPageActive() {
  return detailsPageActive;
}

void displayBegin()'''
text, count = re.subn(weather_block, weather_repl, text, count=1, flags=re.S)
assert count == 1, 'weather block replacement failed'

path.write_text(text)
