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

#include <LovyanGFX.hpp>

// -----------------------------------------------------------------------------
// Native LILYGO T-Display-S3 LovyanGFX profile.
//
// The production firmware defines the board profile directly instead of using
// LilyGo-display-library. This avoids version coupling between that wrapper
// and LovyanGFX's ESP32-S3 Parallel8 implementation.
// -----------------------------------------------------------------------------
class WS5000_TDisplayS3 : public lgfx::LGFX_Device {
  lgfx::Panel_ST7789 _panel;
  lgfx::Bus_Parallel8 _bus;
  lgfx::Light_PWM _light;

public:
  WS5000_TDisplayS3() {
    {
      auto cfg = _bus.config();

      cfg.freq_write = 20000000;

      cfg.pin_wr = 8;
      cfg.pin_rd = 9;
      cfg.pin_rs = 7;

      cfg.pin_d0 = 39;
      cfg.pin_d1 = 40;
      cfg.pin_d2 = 41;
      cfg.pin_d3 = 42;
      cfg.pin_d4 = 45;
      cfg.pin_d5 = 46;
      cfg.pin_d6 = 47;
      cfg.pin_d7 = 48;

      _bus.config(cfg);
      _panel.setBus(&_bus);
    }

    {
      auto cfg = _panel.config();

      cfg.pin_cs = 6;
      cfg.pin_rst = 5;
      cfg.pin_busy = -1;

      cfg.panel_width = 170;
      cfg.panel_height = 320;
      cfg.offset_x = 35;
      cfg.offset_y = 0;
      cfg.offset_rotation = 0;

      cfg.dummy_read_pixel = 8;
      cfg.dummy_read_bits = 1;

      cfg.readable = false;
      cfg.invert = true;
      cfg.rgb_order = false;
      cfg.dlen_16bit = false;
      cfg.bus_shared = true;

      _panel.config(cfg);
    }

    {
      auto cfg = _light.config();

      cfg.pin_bl = 38;
      cfg.invert = false;
      cfg.freq = 44100;
      cfg.pwm_channel = 0;

      _light.config(cfg);
      _panel.setLight(&_light);
    }

    setPanel(&_panel);
  }
};

WS5000_TDisplayS3 display;

static const uint16_t C_BLACK = 0x0000;
static const uint16_t C_WHITE = 0xFFFF;

static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return display.color565(r, g, b);
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

static void drawIconBitmap(int x, int y, const uint16_t *icon) {
  for (int iy = 0; iy < UI_ICON_H; iy++) {
    for (int ix = 0; ix < UI_ICON_W; ix++) {
      uint16_t px = pgm_read_word(&icon[iy * UI_ICON_W + ix]);
      if (px != UI_ICON_TRANSPARENT) display.drawPixel(x + ix, y + iy, px);
    }
  }
}

void drawWiFiIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_WIFI); }
void drawThermometer(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y, ICON_THERMOMETER); }
void drawDrop(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y, ICON_DROP); }
void drawWindIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y - 2, ICON_WIND); }
void drawCompassIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_COMPASS); }
void drawLeafIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_LEAF); }
void drawTrendIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x, y, ICON_TREND); }
void drawSunIcon(int x, int y, uint16_t color) { (void)color; drawIconBitmap(x - 10, y - 10, ICON_SUN); }

void drawMetricCard(int x, int y, int w, int h) {
  const uint16_t bg = rgb565(3, 27, 45);
  const uint16_t border = rgb565(11, 82, 119);
  display.fillRoundRect(x, y, w, h, 7, bg);
  display.drawRoundRect(x, y, w, h, 7, border);
}

static void drawBoldText(const String &text, int x, int y, uint16_t color) {
  display.setTextColor(color);
  display.drawString(text, x, y);
  display.drawString(text, x + 1, y);
  display.drawString(text, x, y + 1);
}

String signedTempDelta(float value) {
  if (!isfinite(value)) return "--";
  String s;
  if (value >= 0.0f) s += "+";
  s += String(value, 1);
  s += String("\xB0");
  s += "F";
  return s;
}

void drawForecastHighLowCard() {
  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t yellow = rgb565(255, 205, 35);
  const bool tomorrow = forecastShowsTomorrow();

  drawMetricCard(7, 258, 156, 29);
  drawSunIcon(20, 272, yellow);

  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font0);
  drawBoldText(tomorrow ? "TOMORROW HIGH / LOW F" : "TODAY HIGH / LOW F", 37, 264, cyan);

  String hl = "-- / --";
  if (wx.forecastValid) {
    float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high) && isfinite(low)) {
      hl = String((int)lroundf(high)) + String("\xB0") + " / " + String((int)lroundf(low)) + String("\xB0");
    }
  }

  display.setFont(&fonts::Font4);
  drawBoldText(hl, 37, 278, C_WHITE);
}


void drawHeader() {
  display.setTextDatum(textdatum_t::middle_left);

  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() <= 12) {
    display.setFont(&fonts::Font4);
  } else {
    display.setFont(&fonts::Font2);
    if (station.length() > 18) station = station.substring(0, 18);
  }

  drawBoldText(station, 8, 24, C_WHITE);
  display.drawFastHLine(8, 48, 154, rgb565(45, 205, 235));
}

void drawFooter() {
  uint16_t bg = rgb565(4, 31, 51);
  uint16_t border = rgb565(10, 63, 100);

  display.fillRect(0, 290, 170, 30, C_BLACK);
  display.fillRoundRect(8, 294, 154, 22, 6, bg);
  display.drawRoundRect(8, 294, 154, 22, 6, border);

  display.setFont(&fonts::Font0);
  display.setTextDatum(textdatum_t::middle_center);
  display.setTextColor(C_WHITE, bg);

  if (WiFi.status() != WL_CONNECTED) {
    display.drawString(setupApStarted ? "Setup 192.168.4.1" : "Wi-Fi disconnected", 85, 305);
    return;
  }
  if (!apiConfigured()) {
    display.drawString("Open /config", 85, 305);
    return;
  }
  if (!wx.valid) {
    display.setTextColor(lastApiError.length() ? rgb565(255, 105, 90) : C_WHITE, bg);
    display.drawString(lastApiError.length() ? "Weather API error" : "Fetching weather...", 85, 305);
    return;
  }

  String footer = "Updated ";
  footer += updateClockText();
  if (dataStale()) {
    footer = "STALE - " + footer;
    display.setTextColor(rgb565(255, 105, 90), bg);
  }
  display.drawString(footer, 85, 305);
}

void drawWaitingScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  display.setTextDatum(textdatum_t::middle_center);
  display.setTextColor(C_WHITE, C_BLACK);
  display.setFont(&fonts::Font4);
  display.drawString(setupApStarted ? "SETUP" : "WAITING", 85, 112);

  display.setFont(&fonts::Font2);
  display.setTextColor(rgb565(175, 182, 192), C_BLACK);
  if (setupApStarted) {
    display.drawString("Connect to setup Wi-Fi", 85, 148);
    display.setFont(&fonts::Font0);
    display.setTextColor(rgb565(65, 205, 255), C_BLACK);
    display.drawString(setupApName(), 85, 180);
    display.drawString("192.168.4.1/config", 85, 198);
  } else if (WiFi.status() == WL_CONNECTED) {
    display.drawString(apiConfigured() ? weatherSourceLabel() : String("API setup needed"), 85, 150);
    display.setFont(&fonts::Font0);
    display.setTextColor(rgb565(65, 205, 255), C_BLACK);
    display.drawString(WiFi.localIP().toString(), 85, 184);
    display.drawString("/config", 85, 202);
  } else {
    display.drawString("Connecting to Wi-Fi", 85, 154);
  }

  drawFooter();
}

void drawWeatherScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  const uint16_t cyan = rgb565(78, 215, 255);
  const uint16_t muted = rgb565(165, 190, 205);
  const uint16_t green = rgb565(120, 225, 70);
  const uint16_t cardBg = rgb565(3, 27, 45);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);

  // Main apparent-temperature card.
  display.fillRoundRect(8, 54, 154, 88, 10, risk.panel);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentTitle(), 85, 66, C_WHITE);

  String value = String((int)lroundf(apparentF));
  display.setFont(&fonts::Font7);
  display.setTextColor(C_WHITE);
  display.drawString(value, 73, 96);

  int valueWidth = display.textWidth(value);
  int rightEdge = 73 + valueWidth / 2;
  display.drawCircle(rightEdge + 5, 81, 3, C_WHITE);

  display.setFont(&fonts::Font4);
  display.drawString("F", rightEdge + 17, 103);

  display.fillRoundRect(16, 118, 138, 18, 6, risk.status);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentRiskLabel(), 85, 127, C_WHITE);

  // Compact metric cards use a consistent hierarchy: label first, value below.
  display.setTextDatum(textdatum_t::middle_left);

  // Temperature
  drawMetricCard(7, 147, 77, 34);
  drawThermometer(13, 153, rgb565(255, 70, 55));
  display.setFont(&fonts::Font0);
  drawBoldText("TEMP", 29, 157, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(String(wx.tempF, 1) + String("\xB0") + "F", 29, 173, C_WHITE);

  // Humidity
  drawMetricCard(87, 147, 76, 34);
  drawDrop(99, 153, rgb565(50, 165, 255));
  display.setFont(&fonts::Font0);
  drawBoldText("HUMIDITY", 113, 157, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(String((int)lroundf(wx.humidity)) + "%", 113, 173, C_WHITE);

  // Dew point
  drawMetricCard(7, 184, 77, 34);
  drawLeafIcon(19, 198, green);
  display.setFont(&fonts::Font0);
  drawBoldText("DEW POINT", 31, 194, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String("\xB0") + "F" : "--", 31, 210, C_WHITE);

  // Difference from yesterday
  drawMetricCard(87, 184, 76, 34);
  drawTrendIcon(94, 195, cyan);
  display.setFont(&fonts::Font0);
  drawBoldText("VS YDAY", 113, 194, cyan);
  display.setFont(&fonts::Font2);
  drawBoldText(signedTempDelta(wx.fromYesterdayF), 113, 210, C_WHITE);

  // Wind / gust
  drawMetricCard(7, 221, 77, 34);
  drawWindIcon(13, 232, cyan);
  display.setFont(&fonts::Font0);
  drawBoldText("W/G MPH", 31, 231, cyan);
  String windLine = isfinite(wx.windMph) ? String(wx.windMph, 1) : "--";
  windLine += " / ";
  windLine += isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--";
  display.setFont(&fonts::Font0);
  drawBoldText(windLine, 34, 242, C_WHITE);

  // Direction
  drawMetricCard(87, 221, 76, 34);
  drawCompassIcon(100, 238, cyan);
  display.setFont(&fonts::Font0);
  drawBoldText("DIR", 115, 231, cyan);
  String degText = isfinite(wx.windDirDeg)
                 ? String((int)lroundf(wx.windDirDeg)) + String("\xB0")
                 : "--";
  String dirLine = degText;
  if (isfinite(wx.windDirDeg)) {
    dirLine += " ";
    dirLine += directionText(wx.windDirDeg);
  }
  display.setFont(&fonts::Font0);
  drawBoldText(dirLine, 115, 248, C_WHITE);

  drawForecastHighLowCard();
  drawFooter();
}

void displayBegin() {
  display.init();
  display.setRotation(0);
  display.setBrightness(255);
  display.fillScreen(C_BLACK);
}
