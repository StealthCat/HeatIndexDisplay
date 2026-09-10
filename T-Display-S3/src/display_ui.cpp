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

// The t-display branch uses two runtime pages. The full-screen apparent
// temperature page is the default; either physical button toggles details.
static bool detailsPageActive = false;
static bool waitingScreenActive = true;

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

static void drawDetailMetricCard(int x, int y, int w, int h,
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
      hl = String((int)lroundf(high)) + String("\xB0") + " / " +
           String((int)lroundf(low)) + String("\xB0");
    }
  }

  display.setFont(&fonts::Font4);
  drawBoldText(hl, 85, 244, C_WHITE);
}

void drawHeader() {
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";

  // Leave enough room for the full date at upper-right, matching Waveshare.
  // Short station names can keep the larger face; typical names such as
  // "Cronin Farm" use Font2 so the header remains clean at 170 px wide.
  display.setTextDatum(textdatum_t::middle_left);
  if (station.length() <= 7) {
    display.setFont(&fonts::Font4);
  } else {
    display.setFont(&fonts::Font2);
    if (station.length() > 14) station = station.substring(0, 14);
  }
  drawBoldText(station, 8, 18, C_WHITE);

  String dateStr = currentDateText();
  display.setFont(&fonts::Font0);
  display.setTextSize(0.62f);
  display.setTextDatum(textdatum_t::middle_right);
  display.setTextColor(rgb565(219, 231, 238));
  display.drawString(dateStr, 162, 18);

  display.setTextDatum(textdatum_t::middle_left);
  display.setTextSize(0.72f);
  display.setTextColor(rgb565(159, 190, 209));
  display.drawString("CURRENT CONDITIONS", 27, 34);
  display.setTextSize(1.0f);
  display.drawFastHLine(8, 34, 12, rgb565(126, 200, 232));
}

static void drawHeroStatusCard() {
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


void drawWaitingScreen() {
  waitingScreenActive = true;
  display.fillScreen(C_BLACK);
  drawHeader();

  // Waiting state owns the complete content area between header and footer.
  drawConceptCard(8, 43, 154, 244, 11, true);
  display.setTextDatum(textdatum_t::middle_center);
  display.setFont(&fonts::Font4);
  display.setTextSize(1.0f);
  display.setTextColor(C_WHITE);
  display.drawString(setupApStarted ? "SETUP" : "WAITING", 85, 148);

  display.setFont(&fonts::Font2);
  display.setTextColor(rgb565(159, 183, 201));
  if (setupApStarted) {
    display.drawString("Connect to setup Wi-Fi", 85, 177);
    display.setFont(&fonts::Font0);
    display.setTextSize(0.85f);
    display.setTextColor(rgb565(114, 202, 255));
    display.drawString(setupApName(), 85, 199);
    display.setTextSize(1.0f);
  } else {
    display.drawString(lastApiError.length() ? "Weather API error" : "Preparing display", 85, 177);
    display.setFont(&fonts::Font0);
    display.setTextSize(0.85f);
    display.setTextColor(rgb565(114, 202, 255));
    if (WiFi.status() != WL_CONNECTED) {
      display.drawString("Connecting to Wi-Fi...", 85, 199);
    } else if (!apiConfigured()) {
      display.drawString("API setup needed", 85, 199);
    } else if (lastApiError.length()) {
      display.drawString("Check provider configuration", 85, 199);
    } else {
      display.drawString("Fetching weather...", 85, 199);
    }
    display.setTextSize(1.0f);
  }

  drawFooter();
}

static void drawFullScreenApparentValue(float apparentF) {
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

  const String temp = isfinite(wx.tempF) ? String(wx.tempF, 1) + String("\xB0") + "F" : "--";
  const String humidity = isfinite(wx.humidity) ? String((int)lroundf(wx.humidity)) + "%" : "--";
  const String dew = isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + String("\xB0") + "F" : "--";
  const String delta = signedTempDelta(wx.fromYesterdayF);

  String wind = isfinite(wx.windMph) ? String(wx.windMph, 1) : "--";
  wind += " / ";
  wind += isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--";

  String direction = "--";
  if (isfinite(wx.windDirDeg)) {
    direction = String((int)lroundf(wx.windDirDeg)) + String("\xB0") + " " + directionText(wx.windDirDeg);
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
  Serial.printf("T-Display page: %s\n", detailsPageActive ? "details" : "heat-index");
  drawWeatherScreen();
}

bool displayDetailPageActive() {
  return detailsPageActive;
}

void displayBegin() {
  display.init();
  display.setRotation(0);
  display.setBrightness(255);
  display.fillScreen(C_BLACK);
}
