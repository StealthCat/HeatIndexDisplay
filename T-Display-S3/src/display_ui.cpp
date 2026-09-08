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
  uint16_t panelTop;
  uint16_t panelBottom;
  uint16_t border;
  uint16_t status;
  uint16_t accent;
};

// The linked NWS HeatRisk graphic uses the progression
// green -> yellow -> orange -> red -> magenta. HeatRisk itself is a forecast
// product that also considers climatology, duration and overnight relief, so
// this display does not claim to calculate HeatRisk. Instead, the Concept 1
// hero uses that NWS color progression as a visual guide while retaining the
// existing NWS heat-index thresholds and labels used by this firmware.
RiskStyle riskFor(float apparentF) {
  if (windChillApplies()) {
    // The NWS wind-chill chart colors indicate approximate frostbite time:
    // light blue = 30 minutes, deeper blue = 10 minutes, purple = 5 minutes.
    // The NWS threshold guidance is approximately -18F, -32F and -48F.
    // Concept 1 keeps its dark vertical-gradient treatment while following
    // that progression as the calculated wind chill becomes more dangerous.
    if (apparentF <= -48.0f) {
      return {"", rgb565(108, 58, 168), rgb565(31, 15, 67),
              rgb565(190, 132, 242), rgb565(39, 18, 79), rgb565(219, 172, 255)};
    }
    if (apparentF <= -32.0f) {
      return {"", rgb565(37, 105, 184), rgb565(10, 34, 78),
              rgb565(99, 171, 255), rgb565(9, 30, 67), rgb565(139, 198, 255)};
    }
    if (apparentF <= -18.0f) {
      return {"", rgb565(78, 166, 218), rgb565(13, 61, 96),
              rgb565(158, 223, 255), rgb565(11, 48, 76), rgb565(194, 235, 255)};
    }
    return {"", rgb565(18, 79, 134), rgb565(6, 25, 44),
            rgb565(88, 183, 255), rgb565(8, 28, 49), rgb565(123, 201, 255)};
  }

  if (apparentF >= 125.0f) {
    return {"", rgb565(178, 21, 133), rgb565(55, 8, 47),
            rgb565(244, 87, 204), rgb565(76, 10, 64), rgb565(255, 139, 228)};
  }
  if (apparentF >= 103.0f) {
    return {"", rgb565(216, 59, 53), rgb565(70, 17, 15),
            rgb565(255, 113, 104), rgb565(82, 18, 14), rgb565(255, 140, 130)};
  }
  if (apparentF >= 90.0f) {
    return {"", rgb565(221, 117, 29), rgb565(71, 30, 8),
            rgb565(255, 173, 75), rgb565(88, 35, 7), rgb565(255, 192, 110)};
  }
  if (apparentF >= 80.0f) {
    return {"", rgb565(197, 155, 23), rgb565(66, 50, 7),
            rgb565(255, 228, 94), rgb565(91, 68, 7), rgb565(255, 235, 128)};
  }
  return {"", rgb565(40, 122, 69), rgb565(10, 35, 20),
          rgb565(97, 216, 137), rgb565(18, 58, 32), rgb565(143, 232, 170)};
}

static uint16_t lerp565(uint16_t a, uint16_t b, float t) {
  int ar = (a >> 11) & 0x1F;
  int ag = (a >> 5) & 0x3F;
  int ab = a & 0x1F;
  int br = (b >> 11) & 0x1F;
  int bg = (b >> 5) & 0x3F;
  int bb = b & 0x1F;

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
    if (lineW > 0) {
      display.drawFastHLine(x + inset, y + row, lineW, lerp565(top, bottom, t));
    }
  }
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

static void drawBoldText(const String &text, int x, int y, uint16_t color) {
  display.setTextColor(color);
  display.drawString(text, x, y);
  display.drawString(text, x + 1, y);
  display.drawString(text, x, y + 1);
}

static void drawConceptCard(int x, int y, int w, int h, int radius = 7, bool highlight = false) {
  const uint16_t bg = highlight ? rgb565(7, 29, 44) : rgb565(4, 22, 34);
  const uint16_t border = rgb565(23, 78, 108);
  display.fillRoundRect(x, y, w, h, radius, bg);
  display.drawRoundRect(x, y, w, h, radius, border);
}

void drawMetricCard(int x, int y, int w, int h) {
  drawConceptCard(x, y, w, h, 6, false);
}

static void drawHeroSun(int cx, int cy) {
  const uint16_t yellow = rgb565(255, 193, 43);
  const uint16_t light = rgb565(255, 220, 96);
  display.fillCircle(cx, cy, 10, yellow);
  display.drawCircle(cx, cy, 10, light);
  for (int i = -1; i <= 1; i += 2) {
    display.drawFastHLine(cx + i * 15 - (i < 0 ? 5 : 0), cy, 5, yellow);
    display.drawFastVLine(cx, cy + i * 15 - (i < 0 ? 5 : 0), 5, yellow);
  }
  display.drawLine(cx - 13, cy - 13, cx - 9, cy - 9, yellow);
  display.drawLine(cx + 9, cy + 9, cx + 13, cy + 13, yellow);
  display.drawLine(cx - 13, cy + 13, cx - 9, cy + 9, yellow);
  display.drawLine(cx + 9, cy - 9, cx + 13, cy - 13, yellow);
}

static void drawHeroWind(int x, int y) {
  const uint16_t blue = rgb565(82, 190, 255);
  display.drawLine(x, y, x + 30, y, blue);
  display.drawLine(x + 24, y - 4, x + 30, y, blue);
  display.drawLine(x + 24, y + 4, x + 30, y, blue);
  display.drawLine(x - 3, y + 9, x + 25, y + 9, blue);
  display.drawLine(x + 19, y + 5, x + 25, y + 9, blue);
  display.drawLine(x + 19, y + 13, x + 25, y + 9, blue);
  display.drawLine(x + 3, y + 18, x + 29, y + 18, blue);
}

static void drawAlertTriangle(int cx, int cy, uint16_t color) {
  display.fillTriangle(cx, cy - 6, cx - 6, cy + 5, cx + 6, cy + 5, color);
  display.drawFastVLine(cx, cy - 2, 4, C_BLACK);
  display.fillCircle(cx, cy + 3, 1, C_BLACK);
}

static void drawClockIcon(int cx, int cy, uint16_t color) {
  display.drawCircle(cx, cy, 6, color);
  display.drawFastVLine(cx, cy - 3, 4, color);
  display.drawLine(cx, cy, cx + 3, cy + 2, color);
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

static void drawMetricLabelValue(int x, int y, const String &label, const String &value) {
  const uint16_t cyan = rgb565(114, 202, 255);
  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.80f);
  drawBoldText(label, x, y, cyan);
  display.setTextSize(1.0f);
  display.setFont(&fonts::Font2);
  drawBoldText(value, x, y + 12, C_WHITE);
}

static void drawApparentTemperature(float apparentF) {
  String value = String((int)lroundf(apparentF));
  const int digits = value.length();

  display.setTextDatum(textdatum_t::middle_center);
  display.setTextColor(C_WHITE);

  if (digits >= 3) {
    display.setFont(&fonts::Font7);
    display.drawString(value, 98, 98);
    display.drawCircle(133, 83, 3, C_WHITE);
    display.setFont(&fonts::Font4);
    display.drawString("F", 145, 101);
  } else {
    display.setFont(&fonts::Font7);
    display.drawString(value, 102, 98);
    display.drawCircle(132, 83, 3, C_WHITE);
    display.setFont(&fonts::Font4);
    display.drawString("F", 144, 101);
  }
}

void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();

  drawConceptCard(7, 252, 156, 35, 7, true);
  drawSunIcon(23, 269, rgb565(255, 193, 43));

  display.setTextDatum(textdatum_t::middle_left);
  display.setFont(&fonts::Font0);
  display.setTextSize(0.80f);
  drawBoldText(tomorrow ? "TOMORROW HIGH / LOW" : "TODAY HIGH / LOW", 40, 260, muted);
  display.setTextSize(1.0f);

  String hl = "-- / --";
  if (wx.forecastValid) {
    float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
    float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
    if (isfinite(high) && isfinite(low)) {
      hl = String((int)lroundf(high)) + String("\xB0") + " / " +
           String((int)lroundf(low)) + String("\xB0");
    }
  }

  display.setFont(&fonts::Font4);
  drawBoldText(hl, 40, 276, C_WHITE);
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
  drawBoldText(station, 8, 18, C_WHITE);

  display.setFont(&fonts::Font0);
  display.setTextSize(0.72f);
  display.setTextColor(rgb565(159, 190, 209));
  display.drawString("CURRENT CONDITIONS", 27, 34);
  display.setTextSize(1.0f);
  display.drawFastHLine(8, 34, 12, rgb565(126, 200, 232));
}

void drawFooter() {
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
  if (!wx.valid) {
    display.setTextDatum(textdatum_t::middle_center);
    display.setTextColor(lastApiError.length() ? red : C_WHITE);
    display.drawString(lastApiError.length() ? "Weather API error" : "Fetching weather...", 85, 304);
    return;
  }

  const bool stale = dataStale();
  const uint16_t stateColor = stale ? red : green;
  drawClockIcon(18, 304, muted);

  String left = "Updated ";
  left += updateClockText();

  display.setTextDatum(textdatum_t::middle_left);
  display.setTextColor(stale ? red : C_WHITE);
  display.drawString(left, 31, 304);

  display.drawFastVLine(119, 297, 13, rgb565(85, 115, 133));
  display.fillCircle(130, 304, 2, stateColor);

  display.setTextDatum(textdatum_t::middle_right);
  display.setTextColor(stateColor);
  drawBoldText(stale ? "STALE" : "ONLINE", 157, 304, stateColor);
}

void drawWaitingScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  drawConceptCard(8, 48, 154, 95, 11, true);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font4);
  display.setTextColor(C_WHITE);
  display.drawString(setupApStarted ? "SETUP" : "WAITING", 85, 84);

  display.setFont(&fonts::Font2);
  display.setTextColor(rgb565(159, 183, 201));
  if (setupApStarted) {
    display.drawString("Connect to setup Wi-Fi", 85, 108);
    display.setFont(&fonts::Font0);
    display.setTextColor(rgb565(114, 202, 255));
    display.drawString(setupApName(), 85, 126);
  } else if (WiFi.status() == WL_CONNECTED) {
    display.drawString(apiConfigured() ? weatherSourceLabel() : String("API setup needed"), 85, 108);
  } else {
    display.drawString("Connecting to Wi-Fi", 85, 108);
  }

  drawFooter();
}

void drawWeatherScreen() {
  display.fillScreen(C_BLACK);
  drawHeader();

  const uint16_t cyan = rgb565(114, 202, 255);
  const uint16_t green = rgb565(123, 220, 71);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);
  const bool cold = windChillApplies();

  // Concept 1 hero panel. Heat Index follows the NWS-inspired HeatRisk
  // progression; Wind Chill follows the NWS frostbite-time chart colors.
  fillGradientRoundRect(8, 43, 154, 101, 11, risk.panelTop, risk.panelBottom);
  display.drawRoundRect(8, 43, 154, 101, 11, risk.border);

  if (cold) drawHeroWind(18, 82);
  else drawHeroSun(32, 88);

  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font2);
  drawBoldText(apparentTitle(), 117, 61, C_WHITE);
  drawApparentTemperature(apparentF);

  display.fillRoundRect(16, 116, 138, 20, 10, risk.status);
  display.drawRoundRect(16, 116, 138, 20, 10, risk.accent);
  drawAlertTriangle(31, 126, risk.accent);
  display.setFont(&fonts::Font0);
  drawBoldText(apparentRiskLabel(), 90, 126, risk.accent);

  // Metric cards: icon left, label above value.
  drawMetricCard(7, 149, 77, 31);
  drawThermometer(12, 155, rgb565(255, 92, 75));
  drawMetricLabelValue(31, 158, "TEMPERATURE", String(wx.tempF, 1) + String("\xB0") + "F");

  drawMetricCard(87, 149, 76, 31);
  drawDrop(99, 155, rgb565(72, 186, 255));
  drawMetricLabelValue(112, 158, "HUMIDITY", String((int)lroundf(wx.humidity)) + "%");

  drawMetricCard(7, 183, 77, 31);
  drawLeafIcon(19, 198, green);
  drawMetricLabelValue(31, 192, "DEW POINT",
    isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String("\xB0") + "F" : "--");

  drawMetricCard(87, 183, 76, 31);
  drawTrendIcon(93, 189, cyan);
  drawMetricLabelValue(112, 192, "VS YDAY", signedTempDelta(wx.fromYesterdayF));

  drawMetricCard(7, 217, 77, 31);
  drawWindIcon(12, 226, cyan);
  String windLine = isfinite(wx.windMph) ? String(wx.windMph, 1) : "--";
  windLine += " / ";
  windLine += isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--";
  drawMetricLabelValue(31, 226, "W/G MPH", windLine);

  drawMetricCard(87, 217, 76, 31);
  drawCompassIcon(99, 233, cyan);
  String dirLine = "--";
  if (isfinite(wx.windDirDeg)) {
    dirLine = String((int)lroundf(wx.windDirDeg)) + String("\xB0") + " " + directionText(wx.windDirDeg);
  }
  drawMetricLabelValue(112, 226, "DIR", dirLine);

  drawForecastHighLowCard();
  drawFooter();
}

void displayBegin() {
  display.init();
  display.setRotation(0);
  display.setBrightness(255);
  display.fillScreen(C_BLACK);
}
