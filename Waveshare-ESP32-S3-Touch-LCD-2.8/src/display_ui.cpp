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
  if (windChillApplies()) {
    if (apparentF <= -35.0f) return {"EXTREME DANGER", rgb565(16, 78, 185), rgb565(8, 48, 125)};
    if (apparentF <= -20.0f) return {"DANGER", rgb565(20, 105, 215), rgb565(10, 62, 150)};
    if (apparentF <= 0.0f)   return {"VERY COLD", rgb565(22, 125, 230), rgb565(12, 75, 165)};
    if (apparentF <= 20.0f)  return {"COLD", rgb565(25, 140, 240), rgb565(14, 82, 175)};
    return {"CHILLY", rgb565(35, 150, 240), rgb565(18, 92, 180)};
  }
  if (apparentF >= 125.0f) return {"EXTREME DANGER", rgb565(205, 25, 55), rgb565(135, 10, 35)};
  if (apparentF >= 103.0f) return {"DANGER", rgb565(235, 35, 30), rgb565(170, 20, 15)};
  if (apparentF >= 90.0f)  return {"EXTREME CAUTION", rgb565(240, 105, 15), rgb565(165, 60, 5)};
  if (apparentF >= 80.0f)  return {"CAUTION", rgb565(240, 165, 20), rgb565(165, 100, 5)};
  return {"NORMAL", rgb565(35, 130, 75), rgb565(15, 82, 42)};
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

void drawRoundedRectCard(int x, int y, int w, int h) {
  const uint16_t bg = rgb565(3, 27, 45);
  const uint16_t border = rgb565(11, 82, 119);
  gfx->fillRoundRect(x, y, w, h, 8, bg);
  gfx->drawRoundRect(x, y, w, h, 8, border);
}

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

void drawSunIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_SUN); }

String directionLongText(float deg) {
  if (!isfinite(deg)) return "--";
  static const char* dirs[] = {
    "North", "Northeast", "East", "Southeast",
    "South", "Southwest", "West", "Northwest"
  };
  int idx = (int)floorf((deg + 22.5f) / 45.0f) % 8;
  return String(dirs[idx]);
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

void drawForecastHighLowCard() {
  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t muted = rgb565(165, 190, 205);
  const uint16_t yellow = rgb565(255, 205, 35);
  const bool tomorrow = forecastShowsTomorrow();

  drawRoundedRectCard(143, 217, 87, 48);
  drawSunIcon(157, 241, yellow);

  printBoldAt(174, 219, tomorrow ? "TOMORROW" : "TODAY", cyan, 1);
  printBoldAt(174, 229, "HIGH / LOW F", muted, 1);

  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
  if (wx.forecastValid && isfinite(high) && isfinite(low)) {
    String highText = String((int)lroundf(high)) + String((char)247);
    String lowText = String((int)lroundf(low)) + String((char)247);
    // Text size 2 is the largest classic-font scale that allows both
    // degree-marked temperatures to fit this 87-pixel card. Spread the two
    // values across the available width and keep the slash visually centered.
    printBoldAt(148, 241, highText, C_WHITE, 2);
    printBoldAt(183, 246, " / ", C_WHITE, 1);
    printBoldAt(192, 241, lowText, C_WHITE, 2);
  } else {
    printBoldAt(166, 241, "-- / --", C_WHITE, 2);
  }
}

void headerText() {
  const uint16_t cyan = rgb565(78, 215, 255);

  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 16) station = station.substring(0, 16);
  printBoldAt(14, 17, station, C_WHITE, 2);

  setText(cyan, 1);
  String dateStr = currentDateText();
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(dateStr, 0, 0, &x1, &y1, &w, &h);
  gfx->setCursor(226 - w, 20);
  gfx->print(dateStr);

  gfx->drawFastHLine(14, 44, 212, cyan);
}

void drawFooter() {
  const uint16_t bg = rgb565(4, 31, 51);
  const uint16_t border = rgb565(10, 63, 100);

  gfx->fillRect(0, 276, 240, 44, C_BLACK);
  gfx->fillRoundRect(10, 282, 220, 28, 7, bg);
  gfx->drawRoundRect(10, 282, 220, 28, 7, border);

  setText(C_WHITE, 1);

  if (WiFi.status() != WL_CONNECTED) {
    gfx->setCursor(18, 293);
    gfx->print(setupApStarted ? "Setup: 192.168.4.1/config" : "Wi-Fi disconnected");
    return;
  }
  if (!apiConfigured()) {
    gfx->setCursor(18, 293);
    gfx->print("Open /config");
    return;
  }
  if (!wx.valid) {
    gfx->setTextColor(lastApiError.length() ? rgb565(255, 105, 90) : C_WHITE);
    gfx->setCursor(18, 293);
    gfx->print(lastApiError.length() ? "Weather API error" : "Fetching weather...");
    return;
  }

  gfx->setCursor(18, 293);
  gfx->print("Updated ");
  gfx->print(updateClockText());

  String right = dataStale() ? "STALE" : "ONLINE";
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(right, 0, 0, &x1, &y1, &w, &h);
  gfx->setTextColor(dataStale() ? rgb565(255, 105, 90) : rgb565(80, 225, 110));
  gfx->setCursor(222 - w, 293);
  gfx->print(right);
}

void drawWaitingScreen() {
  gfx->fillScreen(C_BLACK);
  headerText();

  centerText(setupApStarted ? "SETUP" : "WAITING", 120, 108, 4, C_WHITE);
  centerText(setupApStarted ? "Connect to setup Wi-Fi" : "Preparing display", 120, 148, 1, rgb565(175, 182, 192));

  if (setupApStarted) {
    centerText(setupApName(), 120, 180, 1, rgb565(65, 205, 255));
    centerText("192.168.4.1/config", 120, 206, 2, rgb565(65, 205, 255));
  } else if (WiFi.status() == WL_CONNECTED) {
    centerText(apiConfigured() ? weatherSourceLabel() : String("API setup needed"), 120, 178, 2, rgb565(175, 182, 192));
    centerText(WiFi.localIP().toString(), 120, 204, 2, rgb565(65, 205, 255));
    centerText("Open /config", 120, 230, 1, rgb565(175, 182, 192));
  } else {
    centerText("Connecting to Wi-Fi...", 120, 188, 2, rgb565(175, 182, 192));
  }

  drawFooter();
}

void drawWeatherScreen() {
  gfx->fillScreen(C_BLACK);
  headerText();

  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t cardBg = rgb565(3, 27, 45);
  const uint16_t muted = rgb565(165, 190, 205);
  const uint16_t green = rgb565(120, 225, 70);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);

  // Large apparent-temperature panel.
  gfx->fillRoundRect(10, 65, 128, 148, 12, risk.panel);
  centerBoldText(apparentTitle(), 74, 80, 2, C_WHITE);

  String value = String((int)lroundf(apparentF));

  // Center the complete apparent-temperature group (value + degree mark + F),
  // not just the numeric value. Centering only the digits pushed the degree/F
  // pair against the right edge for three-digit heat indexes such as 100 F.
  setText(C_WHITE, 5);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(value, 0, 0, &x1, &y1, &w, &h);

  setText(C_WHITE, 2);
  int16_t fx1, fy1;
  uint16_t fw, fh;
  gfx->getTextBounds("F", 0, 0, &fx1, &fy1, &fw, &fh);

  const int degreeRadius = 3;
  const int valueDegreeGap = 4;
  const int degreeFGap = 4;
  const int groupWidth = (int)w + valueDegreeGap + (degreeRadius * 2) + degreeFGap + (int)fw;
  const int groupLeft = 74 - groupWidth / 2;

  setText(C_WHITE, 5);
  gfx->setCursor(groupLeft, 110);
  gfx->print(value);

  const int degreeX = groupLeft + (int)w + valueDegreeGap + degreeRadius;
  gfx->drawCircle(degreeX, 114, degreeRadius, C_WHITE);

  const int fX = degreeX + degreeRadius + degreeFGap;
  setText(C_WHITE, 2);
  gfx->setCursor(fX, 124);
  gfx->print("F");

  gfx->fillRoundRect(18, 177, 112, 24, 7, risk.status);
  centerBoldText(apparentRiskLabel(), 74, 184, 1, C_WHITE);

  // Right-side cards: label on top, bold value underneath.
  drawRoundedRectCard(143, 65, 87, 36);
  drawThermometer(150, 73, rgb565(255, 70, 55));
  printBoldAt(169, 76, "TEMP", cyan, 1);
  printBoldAt(169, 91, String(wx.tempF, 1) + String((char)247) + "F", C_WHITE, 2);

  drawRoundedRectCard(143, 102, 87, 36);
  drawDrop(158, 110, rgb565(50, 165, 255));
  printBoldAt(169, 113, "HUMIDITY", cyan, 1);
  printBoldAt(169, 128, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);

  drawRoundedRectCard(143, 139, 87, 36);
  drawLeaf(157, 157, green);
  printBoldAt(169, 150, "DEW POINT", cyan, 1);
  printBoldAt(169, 165, isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String((char)247) + "F" : "--", C_WHITE, 2);

  drawRoundedRectCard(143, 176, 87, 36);
  drawTrend(149, 186, cyan);
  printBoldAt(169, 187, "FROM YDAY", cyan, 1);
  printBoldAt(169, 202, signedTempDelta(wx.fromYesterdayF), C_WHITE, 1);

  // Bottom cards keep the approved geometry but use a clearer label/value hierarchy.
  drawRoundedRectCard(10, 217, 62, 48);
  drawWindIcon(16, 233, cyan);
  centerBoldText("WIND", 41, 219, 1, cyan);
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 53, 229, 2, C_WHITE);
  centerBoldText("mph", 53, 243, 1, muted);
  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"), 41, 251, 1, cyan);
  centerBoldText(String("MAX ") + (isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--"), 41, 258, 1, cyan);

  drawRoundedRectCard(76, 217, 62, 48);
  drawCompassIcon(92, 241, cyan);
  centerBoldText("DIRECTION", 107, 219, 1, cyan);
  String degText = isfinite(wx.windDirDeg)
                 ? String((int)lroundf(wx.windDirDeg)) + String((char)247)
                 : "--";
  centerBoldText(degText, 116, 233, 2, C_WHITE);
  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--", 107, 253, 1, cyan);

  drawForecastHighLowCard();
  drawFooter();
}

void displayBegin() {
  pinMode(LCD_BL, OUTPUT);
  digitalWrite(LCD_BL, HIGH);
  gfx->begin();
  gfx->fillScreen(C_BLACK);
}
