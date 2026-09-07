#include <Arduino.h>
#include <WiFi.h>
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

// Waveshare ESP32-S3-Touch-LCD-2.8 / ESP32-S3-LCD-2.8
#define LCD_MOSI 45
#define LCD_SCLK 40
#define LCD_CS   42
#define LCD_DC   41
#define LCD_RST  39
#define LCD_BL    5

Arduino_DataBus *bus = new Arduino_ESP32SPI(LCD_DC, LCD_CS, LCD_SCLK, LCD_MOSI, GFX_NOT_DEFINED);
Arduino_GFX *gfx = new Arduino_ST7789(bus, LCD_RST, 0, true, 240, 320);

static const uint16_t C_BLACK = 0x0000;
static const uint16_t C_WHITE = 0xFFFF;

static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

struct RiskStyle {
  const char *label;
  uint16_t panel;
  uint16_t status;
};

RiskStyle riskFor(float apparentF) {
  (void)apparentF;
  if (windChillApplies()) {
    return {"", rgb565(10, 52, 94), rgb565(8, 28, 49)};
  }
  return {"", rgb565(108, 40, 14), rgb565(48, 18, 10)};
}

void setText(uint16_t color, uint8_t size) {
  gfx->setTextColor(color);
  gfx->setTextSize(size);
}

void centerText(const String &text, int centerX, int baselineY, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  gfx->setCursor(centerX - (int)w / 2, baselineY);
  gfx->print(text);
}

static void drawIconBitmap(int x, int y, const uint16_t *icon) {
  for (int iy = 0; iy < UI_ICON_H; iy++) {
    for (int ix = 0; ix < UI_ICON_W; ix++) {
      uint16_t px = pgm_read_word(&icon[iy * UI_ICON_W + ix]);
      if (px != UI_ICON_TRANSPARENT) gfx->drawPixel(x + ix, y + iy, px);
    }
  }
}

void drawWiFiIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_WIFI); }
void drawThermometer(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y, ICON_THERMOMETER); }
void drawDrop(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y, ICON_DROP); }
void drawLeaf(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_LEAF); }
void drawTrend(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y - 2, ICON_TREND); }
void drawWindIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y - 2, ICON_WIND); }
void drawCompassIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_COMPASS); }
void drawSunIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_SUN); }

static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t size) {
  setText(color, size);
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
  gfx->setCursor(x, y + 1);
  gfx->print(text);
}

static void centerBoldText(const String &text, int centerX, int y, uint8_t size, uint16_t color) {
  setText(color, size);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  int x = centerX - (int)w / 2;
  gfx->setCursor(x, y);
  gfx->print(text);
  gfx->setCursor(x + 1, y);
  gfx->print(text);
  gfx->setCursor(x, y + 1);
  gfx->print(text);
}

static void drawConceptCard(int x, int y, int w, int h, int radius = 8, bool highlight = false) {
  const uint16_t bg = highlight ? rgb565(7, 29, 44) : rgb565(4, 22, 34);
  const uint16_t border = rgb565(23, 78, 108);
  gfx->fillRoundRect(x, y, w, h, radius, bg);
  gfx->drawRoundRect(x, y, w, h, radius, border);
}

void drawRoundedRectCard(int x, int y, int w, int h) {
  drawConceptCard(x, y, w, h, 8, false);
}

static void drawHeroSun(int cx, int cy) {
  const uint16_t yellow = rgb565(255, 193, 43);
  const uint16_t light = rgb565(255, 220, 96);
  gfx->fillCircle(cx, cy, 13, yellow);
  gfx->drawCircle(cx, cy, 13, light);
  gfx->drawFastHLine(cx - 22, cy, 7, yellow);
  gfx->drawFastHLine(cx + 16, cy, 7, yellow);
  gfx->drawFastVLine(cx, cy - 22, 7, yellow);
  gfx->drawFastVLine(cx, cy + 16, 7, yellow);
  gfx->drawLine(cx - 17, cy - 17, cx - 12, cy - 12, yellow);
  gfx->drawLine(cx + 12, cy + 12, cx + 17, cy + 17, yellow);
  gfx->drawLine(cx - 17, cy + 17, cx - 12, cy + 12, yellow);
  gfx->drawLine(cx + 12, cy - 12, cx + 17, cy - 17, yellow);
}

static void drawHeroWind(int x, int y) {
  const uint16_t blue = rgb565(82, 190, 255);
  gfx->drawLine(x, y, x + 36, y, blue);
  gfx->drawLine(x + 29, y - 5, x + 36, y, blue);
  gfx->drawLine(x + 29, y + 5, x + 36, y, blue);
  gfx->drawLine(x - 2, y + 11, x + 30, y + 11, blue);
  gfx->drawLine(x + 23, y + 6, x + 30, y + 11, blue);
  gfx->drawLine(x + 23, y + 16, x + 30, y + 11, blue);
  gfx->drawLine(x + 4, y + 22, x + 35, y + 22, blue);
}

static void drawAlertTriangle(int cx, int cy, uint16_t color) {
  gfx->fillTriangle(cx, cy - 7, cx - 7, cy + 6, cx + 7, cy + 6, color);
  gfx->drawFastVLine(cx, cy - 2, 5, C_BLACK);
  gfx->fillCircle(cx, cy + 4, 1, C_BLACK);
}

static void drawClockIcon(int cx, int cy, uint16_t color) {
  gfx->drawCircle(cx, cy, 7, color);
  gfx->drawFastVLine(cx, cy - 4, 5, color);
  gfx->drawLine(cx, cy, cx + 4, cy + 2, color);
}

String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s;
  if (value >= 0.0f) s += "+";
  s += String(value, 1);
  s += String((char)247);
  s += "F";
  return s;
}

static void printTempValueCompact(int x, int y, float value) {
  if (!isfinite(value)) {
    printBoldAt(x, y, "--", C_WHITE, 2);
    return;
  }

  String number = String(value, 1);
  setText(C_WHITE, 2);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(number, 0, 0, &x1, &y1, &w, &h);
  printBoldAt(x, y, number, C_WHITE, 2);
  printBoldAt(x + (int)w + 1, y + 7, String((char)247) + "F", C_WHITE, 1);
}

static void drawMetricCardValue(int x, int y, int w, int h, const uint16_t *iconData,
                                int iconX, int iconY, const String &label,
                                const String &value, uint8_t valueSize = 1) {
  drawConceptCard(x, y, w, h, 7, false);
  drawIconBitmap(iconX, iconY, iconData);
  printBoldAt(x + 26, y + 7, label, rgb565(114, 202, 255), 1);
  printBoldAt(x + 26, y + 20, value, C_WHITE, valueSize);
}

static void drawApparentTemperature(float apparentF) {
  String value = String((int)lroundf(apparentF));
  const bool threeDigits = value.length() >= 3;

  if (threeDigits) {
    printBoldAt(55, 122, value, C_WHITE, 4);
    gfx->drawCircle(119, 123, 3, C_WHITE);
    printBoldAt(125, 134, "F", C_WHITE, 2);
  } else {
    printBoldAt(57, 116, value, C_WHITE, 5);
    gfx->drawCircle(118, 119, 3, C_WHITE);
    printBoldAt(124, 132, "F", C_WHITE, 2);
  }
}

void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 182, 198);
  const uint16_t cyan = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();

  drawConceptCard(143, 210, 87, 52, 8, true);
  drawSunIcon(160, 237, rgb565(255, 193, 43));

  centerBoldText(tomorrow ? "TOMORROW" : "TODAY", 188, 214, 1, cyan);
  centerBoldText("HIGH / LOW F", 188, 225, 1, muted);

  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
  if (wx.forecastValid && isfinite(high) && isfinite(low)) {
    String highText = String((int)lroundf(high)) + String((char)247);
    String lowText = String((int)lroundf(low)) + String((char)247);
    printBoldAt(148, 239, highText, C_WHITE, 2);
    printBoldAt(183, 245, "/", C_WHITE, 1);
    printBoldAt(192, 239, lowText, C_WHITE, 2);
  } else {
    centerBoldText("-- / --", 190, 239, 2, C_WHITE);
  }
}

void headerText() {
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 16) station = station.substring(0, 16);
  printBoldAt(12, 12, station, C_WHITE, 2);

  setText(rgb565(219, 231, 238), 1);
  String dateStr = currentDateText();
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(dateStr, 0, 0, &x1, &y1, &w, &h);
  gfx->setCursor(229 - w, 18);
  gfx->print(dateStr);

  printBoldAt(12, 34, "WEATHER STATION", rgb565(157, 184, 202), 1);
  gfx->drawFastHLine(12, 47, 216, rgb565(23, 63, 85));
}

void drawFooter() {
  const uint16_t muted = rgb565(168, 198, 216);
  const uint16_t green = rgb565(117, 237, 79);
  const uint16_t red = rgb565(255, 122, 103);

  gfx->fillRect(0, 267, 240, 53, C_BLACK);
  drawConceptCard(10, 272, 220, 36, 9, true);

  if (WiFi.status() != WL_CONNECTED) {
    centerBoldText(setupApStarted ? "Setup: 192.168.4.1/config" : "Wi-Fi disconnected",
                   120, 285, 1, C_WHITE);
    return;
  }
  if (!apiConfigured()) {
    centerBoldText("Open /config", 120, 285, 1, C_WHITE);
    return;
  }
  if (!wx.valid) {
    centerBoldText(lastApiError.length() ? "Weather API error" : "Fetching weather...",
                   120, 285, 1, lastApiError.length() ? red : C_WHITE);
    return;
  }

  const bool stale = dataStale();
  const uint16_t stateColor = stale ? red : green;
  drawClockIcon(24, 290, muted);

  String left = "Updated ";
  left += updateClockText();
  printBoldAt(45, 286, left, stale ? red : C_WHITE, 1);

  gfx->drawFastVLine(169, 280, 20, rgb565(85, 115, 133));
  gfx->fillCircle(190, 290, 3, stateColor);

  String state = stale ? "STALE" : "ONLINE";
  setText(stateColor, 1);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(state, 0, 0, &x1, &y1, &w, &h);
  printBoldAt(221 - (int)w, 286, state, stateColor, 1);
}

void drawWaitingScreen() {
  gfx->fillScreen(C_BLACK);
  headerText();

  drawConceptCard(10, 54, 220, 150, 12, true);
  centerBoldText(setupApStarted ? "SETUP" : "WAITING", 120, 100, 4, C_WHITE);
  centerText(setupApStarted ? "Connect to setup Wi-Fi" : "Preparing display",
             120, 145, 1, rgb565(159, 183, 201));

  if (setupApStarted) {
    centerText(setupApName(), 120, 170, 1, rgb565(114, 202, 255));
    centerText("192.168.4.1/config", 120, 188, 1, rgb565(114, 202, 255));
  } else if (WiFi.status() == WL_CONNECTED) {
    centerText(apiConfigured() ? weatherSourceLabel() : String("API setup needed"),
               120, 170, 1, rgb565(159, 183, 201));
  } else {
    centerText("Connecting to Wi-Fi...", 120, 170, 1, rgb565(159, 183, 201));
  }

  drawFooter();
}

void drawWeatherScreen() {
  gfx->fillScreen(C_BLACK);
  headerText();

  const uint16_t cyan = rgb565(114, 202, 255);
  const uint16_t muted = rgb565(159, 183, 201);
  const uint16_t green = rgb565(123, 220, 71);
  const uint16_t warmBorder = rgb565(226, 107, 48);
  const uint16_t coldBorder = rgb565(88, 183, 255);
  const uint16_t alertWarm = rgb565(255, 118, 94);
  const uint16_t alertCold = rgb565(123, 201, 255);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);
  const bool cold = windChillApplies();

  // Concept 1 hero panel.
  gfx->fillRoundRect(10, 54, 128, 151, 12, risk.panel);
  gfx->drawRoundRect(10, 54, 128, 151, 12, cold ? coldBorder : warmBorder);

  if (cold) drawHeroWind(20, 88);
  else drawHeroSun(36, 96);

  centerBoldText(apparentTitle(), 101, 70, 1, C_WHITE);
  drawApparentTemperature(apparentF);

  gfx->fillRoundRect(18, 170, 112, 24, 12, risk.status);
  gfx->drawRoundRect(18, 170, 112, 24, 12, cold ? alertCold : alertWarm);
  drawAlertTriangle(32, 182, cold ? alertCold : alertWarm);
  centerBoldText(apparentRiskLabel(), 85, 179, 1, cold ? alertCold : alertWarm);

  // Right-side metric stack.
  drawConceptCard(143, 54, 87, 34, 7, false);
  drawThermometer(148, 61, rgb565(255, 92, 75));
  printBoldAt(169, 60, "TEMP", cyan, 1);
  printTempValueCompact(169, 72, wx.tempF);

  drawConceptCard(143, 91, 87, 34, 7, false);
  drawDrop(157, 98, rgb565(72, 186, 255));
  printBoldAt(169, 97, "HUMIDITY", cyan, 1);
  printBoldAt(169, 109, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);

  drawConceptCard(143, 128, 87, 34, 7, false);
  drawLeaf(157, 145, green);
  printBoldAt(169, 134, "DEW POINT", cyan, 1);
  printTempValueCompact(169, 146, wx.dewPointF);

  drawConceptCard(143, 165, 87, 40, 7, false);
  drawTrend(148, 176, cyan);
  printBoldAt(169, 171, "FROM YDAY", cyan, 1);
  printBoldAt(169, 186, signedTempDelta(wx.fromYesterdayF), C_WHITE, 1);

  // Bottom three cards.
  drawConceptCard(10, 210, 62, 52, 8, true);
  drawWindIcon(15, 226, cyan);
  centerBoldText("WIND", 41, 214, 1, rgb565(157, 200, 228));
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 51, 228, 2, C_WHITE);
  centerBoldText("mph", 51, 242, 1, muted);
  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"),
                 41, 251, 1, rgb565(166, 209, 234));
  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"),
                 41, 258, 1, rgb565(166, 209, 234));

  drawConceptCard(76, 210, 62, 52, 8, true);
  drawCompassIcon(88, 236, cyan);
  centerBoldText("DIRECTION", 107, 214, 1, rgb565(157, 200, 228));
  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg));
    centerBoldText(dirNumber, 116, 229, 2, C_WHITE);
    gfx->drawCircle(135, 231, 2, C_WHITE);
  } else {
    centerBoldText("--", 116, 229, 2, C_WHITE);
  }
  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--",
                 107, 250, 1, rgb565(157, 200, 228));

  drawForecastHighLowCard();
  drawFooter();
}

void displayBegin() {
  pinMode(LCD_BL, OUTPUT);
  digitalWrite(LCD_BL, HIGH);
  gfx->begin();
  gfx->fillScreen(C_BLACK);
}
