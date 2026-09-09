#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <math.h>
#include "app_state.h"
#include "config_store.h"
#include "display_ui.h"
#include "forecast_weather.h"
#include "time_utils.h"
#include "weather_math.h"
#include "wifi_manager.h"
#include "ui_assets.h"

#include <Arduino_GFX_Library.h>

// Waveshare ESP32-S3-Touch-LCD-7C-BOX: 7-inch 800x480 RGB565 ST7262.
// Touch is intentionally unused. Pins/timings follow Waveshare's 7C reference.
static constexpr int LCD_WIDTH = 800;
static constexpr int LCD_HEIGHT = 480;

Arduino_ESP32RGBPanel *rgbpanel = new Arduino_ESP32RGBPanel(
    5, 3, 46, 7,
    1, 2, 42, 41, 40,
    39, 0, 45, 9, 8, 21,
    14, 38, 18, 17, 10,
    0, 8, 4, 8,
    0, 8, 4, 8,
    1, 16000000, false, 0, 0);

Arduino_GFX *gfx = new Arduino_RGB_Display(
    LCD_WIDTH, LCD_HEIGHT, rgbpanel, 0, true);

static const uint16_t C_BLACK = 0x0000;
static const uint16_t C_WHITE = 0xFFFF;

static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

struct RiskStyle {
  uint16_t panelTop;
  uint16_t panelBottom;
  uint16_t border;
  uint16_t status;
  uint16_t accent;
};

RiskStyle riskFor(float apparentF) {
  if (windChillApplies()) {
    if (apparentF <= -48.0f) return {rgb565(108, 58, 168), rgb565(31, 15, 67), rgb565(190, 132, 242), rgb565(39, 18, 79), rgb565(219, 172, 255)};
    if (apparentF <= -32.0f) return {rgb565(37, 105, 184), rgb565(10, 34, 78), rgb565(99, 171, 255), rgb565(9, 30, 67), rgb565(139, 198, 255)};
    if (apparentF <= -18.0f) return {rgb565(78, 166, 218), rgb565(13, 61, 96), rgb565(158, 223, 255), rgb565(11, 48, 76), rgb565(194, 235, 255)};
    return {rgb565(18, 79, 134), rgb565(6, 25, 44), rgb565(88, 183, 255), rgb565(8, 28, 49), rgb565(123, 201, 255)};
  }
  if (apparentF >= 125.0f) return {rgb565(178, 21, 133), rgb565(55, 8, 47), rgb565(244, 87, 204), rgb565(76, 10, 64), rgb565(255, 139, 228)};
  if (apparentF >= 103.0f) return {rgb565(216, 59, 53), rgb565(70, 17, 15), rgb565(255, 113, 104), rgb565(82, 18, 14), rgb565(255, 140, 130)};
  if (apparentF >= 90.0f) return {rgb565(221, 117, 29), rgb565(71, 30, 8), rgb565(255, 173, 75), rgb565(88, 35, 7), rgb565(255, 192, 110)};
  if (apparentF >= 80.0f) return {rgb565(197, 155, 23), rgb565(66, 50, 7), rgb565(255, 228, 94), rgb565(91, 68, 7), rgb565(255, 235, 128)};
  return {rgb565(40, 122, 69), rgb565(10, 35, 20), rgb565(97, 216, 137), rgb565(18, 58, 32), rgb565(143, 232, 170)};
}

static uint16_t lerp565(uint16_t a, uint16_t b, float t) {
  int ar = (a >> 11) & 0x1F, ag = (a >> 5) & 0x3F, ab = a & 0x1F;
  int br = (b >> 11) & 0x1F, bg = (b >> 5) & 0x3F, bb = b & 0x1F;
  int r = ar + (int)lroundf((br - ar) * t);
  int g = ag + (int)lroundf((bg - ag) * t);
  int bl = ab + (int)lroundf((bb - ab) * t);
  return ((uint16_t)r << 11) | ((uint16_t)g << 5) | (uint16_t)bl;
}

static void fillGradientRoundRect(int x, int y, int w, int h, int radius,
                                  uint16_t top, uint16_t bottom) {
  for (int row = 0; row < h; row++) {
    float t = h > 1 ? (float)row / (float)(h - 1) : 0.0f;
    int inset = 0;
    if (row < radius) {
      float dy = (float)(radius - row);
      float inside = (float)(radius * radius) - dy * dy;
      if (inside < 0.0f) inside = 0.0f;
      inset = radius - (int)sqrtf(inside);
    } else if (row >= h - radius) {
      float dy = (float)(row - (h - radius - 1));
      float inside = (float)(radius * radius) - dy * dy;
      if (inside < 0.0f) inside = 0.0f;
      inset = radius - (int)sqrtf(inside);
    }
    int lineW = w - inset * 2;
    if (lineW > 0) gfx->drawFastHLine(x + inset, y + row, lineW, lerp565(top, bottom, t));
  }
}

static void setText(uint16_t color, uint8_t size) {
  gfx->setTextColor(color);
  gfx->setTextSize(size);
}

static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {
  setText(color, size);
  gfx->setCursor(x, y); gfx->print(text);
  gfx->setCursor(x + 1, y); gfx->print(text);
  gfx->setCursor(x, y + 1); gfx->print(text);
}

static void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1; uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  printBoldAt(centerX - (int)w / 2, y, text, color, size);
}

static void rightText(const String &text, int rightX, int y, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1; uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  gfx->setCursor(rightX - (int)w, y);
  gfx->print(text);
}

static void drawConceptCard(int x, int y, int w, int h, int radius = 12, bool highlight = false) {
  const uint16_t bg = highlight ? rgb565(7, 29, 44) : rgb565(4, 22, 34);
  const uint16_t border = rgb565(23, 78, 108);
  gfx->fillRoundRect(x, y, w, h, radius, bg);
  gfx->drawRoundRect(x, y, w, h, radius, border);
}

static void drawIconBitmapScaled(int x, int y, const uint16_t *iconData, uint8_t scale = 2) {
  for (int iy = 0; iy < UI_ICON_H; iy++) {
    for (int ix = 0; ix < UI_ICON_W; ix++) {
      uint16_t px = pgm_read_word(&iconData[iy * UI_ICON_W + ix]);
      if (px != UI_ICON_TRANSPARENT) gfx->fillRect(x + ix * scale, y + iy * scale, scale, scale, px);
    }
  }
}

static void drawHeroSun(int cx, int cy) {
  const uint16_t yellow = rgb565(255, 193, 43), light = rgb565(255, 220, 96);
  gfx->fillCircle(cx, cy, 28, yellow); gfx->drawCircle(cx, cy, 28, light);
  gfx->drawFastHLine(cx - 50, cy, 14, yellow); gfx->drawFastHLine(cx + 37, cy, 14, yellow);
  gfx->drawFastVLine(cx, cy - 50, 14, yellow); gfx->drawFastVLine(cx, cy + 37, 14, yellow);
  gfx->drawLine(cx - 39, cy - 39, cx - 27, cy - 27, yellow); gfx->drawLine(cx + 27, cy + 27, cx + 39, cy + 39, yellow);
  gfx->drawLine(cx - 39, cy + 39, cx - 27, cy + 27, yellow); gfx->drawLine(cx + 27, cy - 27, cx + 39, cy - 39, yellow);
}

static void drawHeroWind(int x, int y) {
  const uint16_t blue = rgb565(82, 190, 255);
  gfx->drawLine(x, y, x + 78, y, blue); gfx->drawLine(x + 63, y - 10, x + 78, y, blue); gfx->drawLine(x + 63, y + 10, x + 78, y, blue);
  gfx->drawLine(x - 5, y + 25, x + 65, y + 25, blue); gfx->drawLine(x + 50, y + 15, x + 65, y + 25, blue); gfx->drawLine(x + 50, y + 35, x + 65, y + 25, blue);
  gfx->drawLine(x + 10, y + 50, x + 76, y + 50, blue);
}

static void drawClockIcon(int cx, int cy, uint16_t color) {
  gfx->drawCircle(cx, cy, 12, color);
  gfx->drawFastVLine(cx, cy - 7, 8, color);
  gfx->drawLine(cx, cy, cx + 7, cy + 4, color);
}

static bool ioExpanderWrite16(uint8_t reg, uint16_t value) {
  Wire.beginTransmission(0x24);
  Wire.write(reg); Wire.write((uint8_t)(value & 0xFF)); Wire.write((uint8_t)((value >> 8) & 0xFF));
  return Wire.endTransmission() == 0;
}

static void enable7CBacklight() {
  Wire.begin(47, 48, 400000);
  delay(20);
  ioExpanderWrite16(0x02, 0xFFFF);
  ioExpanderWrite16(0x03, 0xFFFF);
}

static String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s; if (value >= 0.0f) s += "+";
  s += String(value, 1); s += String((char)247); s += "F";
  return s;
}

static void drawMetricCardValue(int x, int y, int w, int h, const uint16_t *iconData,
                                const String &label, const String &value, uint8_t valueSize = 3) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 12, false);
  drawIconBitmapScaled(x + 12, y + (h - 40) / 2, iconData, 2);
  printBoldAt(x + 64, y + 9, label, cyan, 2);
  printBoldAt(x + 64, y + 27, value, C_WHITE, valueSize);
}

static void drawApparentTemperature(float apparentF) {
  String value = String((int)lroundf(apparentF));
  const uint8_t numberSize = value.length() >= 3 ? 8 : 9;
  const uint8_t unitSize = 4;
  const int centerX = 320, topY = 143;
  setText(C_WHITE, numberSize);
  int16_t x1, y1; uint16_t numberW, numberH;
  gfx->getTextBounds(value, 0, 0, &x1, &y1, &numberW, &numberH);
  setText(C_WHITE, unitSize);
  uint16_t fW, fH; gfx->getTextBounds("F", 0, 0, &x1, &y1, &fW, &fH);
  // Arduino_GFX text bounds include the final character-cell spacing. Pull the
  // degree/F unit into that trailing space so the temperature reads as one
  // compact value instead of leaving a large visual gap after the digits.
  const int groupW = (int)numberW + 10 + (int)fW;
  const int startX = centerX - groupW / 2;
  printBoldAt(startX, topY, value, C_WHITE, numberSize);
  const int unitX = startX + (int)numberW - 4;
  gfx->drawCircle(unitX + 3, topY + 7, 4, C_WHITE);
  printBoldAt(unitX + 12, topY + 20, "F", C_WHITE, unitSize);
}

void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 182, 198), cyan = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();
  drawConceptCard(477, 316, 290, 76, 14, true);
  drawIconBitmapScaled(493, 335, ICON_SUN, 2);
  centerBoldText(tomorrow ? "TOMORROW" : "TODAY", 620, 322, 2, cyan);
  centerBoldText("HIGH / LOW F", 620, 341, 1, muted);
  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
  if (wx.forecastValid && isfinite(high) && isfinite(low)) {
    String value = String((int)lroundf(high)) + String((char)247) + " / " + String((int)lroundf(low)) + String((char)247);
    centerBoldText(value, 635, 355, 4, C_WHITE);
  } else {
    centerBoldText("-- / --", 635, 355, 4, C_WHITE);
  }
}

static void drawHeader() {
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 20) station = station.substring(0, 20);
  printBoldAt(30, 20, station, C_WHITE, station.length() <= 13 ? 4 : 3);
  rightText(currentDateText(), 770, 27, 2, rgb565(219, 231, 238));
  printBoldAt(30, 56, "CURRENT CONDITIONS", rgb565(157, 184, 202), 2);
  gfx->drawFastHLine(30, 76, 740, rgb565(23, 63, 85));
}

void drawFooter() {
  const uint16_t muted = rgb565(168, 198, 216), green = rgb565(117, 237, 79), red = rgb565(255, 122, 103);
  gfx->fillRect(0, 400, LCD_WIDTH, 80, C_BLACK);
  drawConceptCard(33, 410, 734, 52, 14, true);
  if (WiFi.status() != WL_CONNECTED) {
    centerBoldText(setupApStarted ? "Setup: 192.168.4.1/config" : "Wi-Fi disconnected", 400, 427, 2, C_WHITE); return;
  }
  if (!apiConfigured()) { centerBoldText("Open /config", 400, 427, 2, C_WHITE); return; }

  const bool offline = !wx.valid;
  const bool stale = !offline && dataStale();
  const uint16_t stateColor = offline ? red : (stale ? red : green);
  drawClockIcon(67, 436, muted);

  String left;
  String state;
  uint16_t leftColor = C_WHITE;
  if (offline) {
    left = lastApiError.length() ? "Weather API error" : "Fetching weather...";
    state = "OFFLINE";
    leftColor = lastApiError.length() ? red : C_WHITE;
  } else {
    left = "Updated "; left += updateClockText();
    state = stale ? "STALE" : "ONLINE";
    leftColor = stale ? red : C_WHITE;
  }
  printBoldAt(94, 427, left, leftColor, 2);
  gfx->drawFastVLine(570, 419, 34, rgb565(85, 115, 133));

  // 8 px at 800x480 gives the same apparent gap as LILYGO's 4 px.
  gfx->fillCircle(649, 436, 5, stateColor);
  printBoldAt(662, 427, state, stateColor, 2);
}


void drawWaitingScreen() {
  gfx->fillScreen(C_BLACK);
  drawHeader();

  // Waiting state owns the complete content area between header and footer.
  drawConceptCard(33, 82, 734, 310, 18, true);
  centerBoldText(setupApStarted ? "SETUP" : "WAITING", 400, 164, 6, C_WHITE);

  if (setupApStarted) {
    centerBoldText("Connect to setup Wi-Fi", 400, 233, 3, rgb565(159, 183, 201));
    centerBoldText(setupApName(), 400, 281, 2, rgb565(114, 202, 255));
    centerBoldText("192.168.4.1/config", 400, 311, 2, rgb565(114, 202, 255));
  } else {
    centerBoldText(lastApiError.length() ? "Weather API error" : "Preparing display",
                   400, 233, 3, rgb565(159, 183, 201));
    if (WiFi.status() != WL_CONNECTED) {
      centerBoldText("Connecting to Wi-Fi...", 400, 281, 2, rgb565(114, 202, 255));
    } else if (!apiConfigured()) {
      centerBoldText("API setup needed", 400, 281, 2, rgb565(114, 202, 255));
    } else if (lastApiError.length()) {
      centerBoldText("Check provider configuration", 400, 281, 2, rgb565(114, 202, 255));
    } else {
      centerBoldText("Fetching weather...", 400, 281, 2, rgb565(114, 202, 255));
    }
  }

  drawFooter();
}

void drawWeatherScreen() {
  gfx->fillScreen(C_BLACK);
  drawHeader();
  const uint16_t cyan = rgb565(114, 202, 255), muted = rgb565(159, 183, 201);
  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);
  const bool cold = windChillApplies();

  fillGradientRoundRect(33, 82, 427, 225, 18, risk.panelTop, risk.panelBottom);
  gfx->drawRoundRect(33, 82, 427, 225, 18, risk.border);
  if (cold) drawHeroWind(66, 143); else drawHeroSun(110, 160);
  centerBoldText(apparentTitle(), 325, 103, 3, C_WHITE);
  drawApparentTemperature(apparentF);
  gfx->fillRoundRect(60, 260, 373, 34, 17, risk.status);
  gfx->drawRoundRect(60, 260, 373, 34, 17, risk.accent);
  centerBoldText(apparentRiskLabel(), 246, 268, 2, risk.accent);

  drawMetricCardValue(477, 82, 290, 50, ICON_THERMOMETER, "TEMP", isfinite(wx.tempF) ? String(wx.tempF, 1) + String((char)247) + "F" : "--");
  drawMetricCardValue(477, 137, 290, 50, ICON_DROP, "HUMIDITY", isfinite(wx.humidity) ? String((int)lroundf(wx.humidity)) + "%" : "--");
  drawMetricCardValue(477, 192, 290, 50, ICON_LEAF, "DEW POINT", isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String((char)247) + "F" : "--");
  drawMetricCardValue(477, 247, 290, 60, ICON_TREND, "FROM YDAY", signedTempDelta(wx.fromYesterdayF));

  drawConceptCard(33, 316, 207, 76, 14, true);
  drawIconBitmapScaled(48, 337, ICON_WIND, 2);
  centerBoldText("WIND", 136, 322, 2, rgb565(157, 200, 228));
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 160, 342, 4, C_WHITE);
  centerBoldText("mph", 160, 371, 1, muted);
  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"), 136, 380, 1, rgb565(166, 209, 234));
  rightText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"), 225, 380, 1, rgb565(166, 209, 234));

  drawConceptCard(253, 316, 207, 76, 14, true);
  drawIconBitmapScaled(270, 337, ICON_COMPASS, 2);
  centerBoldText("DIRECTION", 356, 322, 2, rgb565(157, 200, 228));
  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg)) + String((char)247);
    centerBoldText(dirNumber, 385, 345, 4, C_WHITE);
    centerBoldText(directionText(wx.windDirDeg), 356, 376, 2, rgb565(157, 200, 228));
  } else {
    centerBoldText("--", 385, 345, 4, C_WHITE);
    centerBoldText("--", 356, 376, 2, rgb565(157, 200, 228));
  }

  drawForecastHighLowCard();
  drawFooter();
}

void displayBegin() {
  gfx->begin();
  enable7CBacklight();
  gfx->fillScreen(C_BLACK);
}
