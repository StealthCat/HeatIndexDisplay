from pathlib import Path

ROOT = Path('.')
P28 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp'
P7 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-7C-BOX/src/display_ui.cpp'
INI28 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-2.8/platformio.ini'
INI7 = ROOT / 'Waveshare-ESP32-S3-Touch-LCD-7C-BOX/platformio.ini'


def between(text, start, end, replacement):
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + replacement + text[j:]

ADAPTER = r'''static lgfx::LGFX_Sprite tDisplayTextRaster;

static const lgfx::IFont *tDisplayFontForTier(uint8_t tier) {
  if (tier <= 1) return &fonts::Font0;  // T-Display native 8 px UI font
  if (tier <= 3) return &fonts::Font2;  // T-Display native 16 px UI font
  return &fonts::Font4;                 // T-Display native 26 px title/unit font
}

static int tDisplayTextWidth(const String &text, const lgfx::IFont *font) {
  tDisplayTextRaster.setFont(font);
  tDisplayTextRaster.setTextSize(1.0f);
  return tDisplayTextRaster.textWidth(text.c_str());
}

static int tDisplayTextWidth(const String &text, uint8_t tier) {
  return tDisplayTextWidth(text, tDisplayFontForTier(tier));
}

static void drawTDisplayTextAt(int x, int y, const String &text,
                               uint16_t color, const lgfx::IFont *font) {
  if (!text.length()) return;
  tDisplayTextRaster.deleteSprite();
  tDisplayTextRaster.setColorDepth(8);
  tDisplayTextRaster.setFont(font);
  tDisplayTextRaster.setTextSize(1.0f);
  tDisplayTextRaster.setTextDatum(lgfx::textdatum_t::top_left);
  const int w = tDisplayTextRaster.textWidth(text.c_str()) + 2;
  const int h = tDisplayTextRaster.fontHeight() + 2;
  if (!tDisplayTextRaster.createSprite(w, h)) return;
  tDisplayTextRaster.fillSprite(0x000000U);
  tDisplayTextRaster.setTextColor(0xFFFFFFU, 0x000000U);
  tDisplayTextRaster.drawString(text.c_str(), 0, 0);
  for (int py = 0; py < h; ++py) {
    for (int px = 0; px < w; ++px) {
      if (tDisplayTextRaster.readPixelValue(px, py) != 0) {
        gfx->drawPixel(x + px, y + py, color);
      }
    }
  }
  tDisplayTextRaster.deleteSprite();
}

static void drawTDisplayTextAt(int x, int y, const String &text,
                               uint16_t color, uint8_t tier) {
  drawTDisplayTextAt(x, y, text, color, tDisplayFontForTier(tier));
}

void setText(uint16_t color, uint8_t tier) {
  // Keep Arduino_GFX's bounds API usable for legacy geometry calculations,
  // while all visible glyphs are rasterized from the exact T-Display fonts.
  gfx->setFont(nullptr);
  gfx->setTextColor(color);
  gfx->setTextSize(tier <= 1 ? 1 : (tier <= 3 ? 2 : 4));
}

void centerText(const String &text, int centerX, int topY, uint8_t tier, uint16_t color) {
  const int w = tDisplayTextWidth(text, tier);
  drawTDisplayTextAt(centerX - w / 2, topY, text, color, tier);
}

static void rightText(const String &text, int rightX, int topY, uint8_t tier, uint16_t color) {
  const int w = tDisplayTextWidth(text, tier);
  drawTDisplayTextAt(rightX - w, topY, text, color, tier);
}

'''

PRINT_HELPERS = r'''static void printBoldAt(int x, int y, const String &text, uint16_t color, uint8_t tier) {
  // Match the T-Display font face and native size, but keep a single raster
  // pass on the Waveshare panels for the cleanest physical-pixel edges.
  drawTDisplayTextAt(x, y, text, color, tier);
}

static void centerBoldText(const String &text, int centerX, int y, uint8_t tier, uint16_t color) {
  centerText(text, centerX, y, tier, color);
}

'''

# ---------------- 2.8-inch display ----------------
s = P28.read_text()
s = s.replace('#include <Arduino_GFX_Library.h>\n#include "fonts/FreeSans8pt7b.h"\n#include "fonts/FreeSans10pt7b.h"\n#include "fonts/FreeSans16pt7b.h"\n#include "fonts/FreeSans18pt7b.h"\n',
              '#include <Arduino_GFX_Library.h>\n#include <LovyanGFX.hpp>\n')
s = between(s, 'static const GFXfont *uiFontForSize', 'static void drawIconBitmap', ADAPTER)
s = between(s, '// FreeSans is rendered', 'static void drawConceptCard', PRINT_HELPERS)

START28 = s.index('static void printTempValueCompact')
END28 = s.index('void displayBegin()', START28)
TAIL28 = r'''static void printTempValueCompact(int x, int y, float value) {
  if (!isfinite(value)) {
    printBoldAt(x, y, "--", C_WHITE, 2);
    return;
  }
  String number = String(value, 1);
  const int w = tDisplayTextWidth(number, 2);
  printBoldAt(x, y, number, C_WHITE, 2);
  gfx->drawCircle(x + w + 3, y + 4, 2, C_WHITE);
  printBoldAt(x + w + 7, y, "F", C_WHITE, 2);
}

static void printSignedTempValueCompact(int x, int y, float value) {
  if (!isfinite(value)) {
    printBoldAt(x, y, "--", C_WHITE, 2);
    return;
  }
  String number = signedTempDelta(value);
  const int w = tDisplayTextWidth(number, 2);
  printBoldAt(x, y, number, C_WHITE, 2);
  gfx->drawCircle(x + w + 3, y + 4, 2, C_WHITE);
  printBoldAt(x + w + 7, y, "F", C_WHITE, 2);
}

static void drawMetricCardValue(int x, int y, int w, int h, const uint16_t *iconData,
                                int iconX, int iconY, const String &label,
                                const String &value, uint8_t valueSize = 2) {
  drawConceptCard(x, y, w, h, 7, false);
  drawIconBitmap(iconX, iconY, iconData);
  printBoldAt(x + 26, y + 5, label, rgb565(114, 202, 255), 1);
  printBoldAt(x + 26, y + 17, value, C_WHITE, valueSize);
}

static void drawApparentTemperature(float apparentF) {
  const String value = String((int)lroundf(apparentF));
  const lgfx::IFont *numberFont = &fonts::Font7;
  const lgfx::IFont *unitFont = &fonts::Font4;
  const int valueW = tDisplayTextWidth(value, numberFont);
  const int fW = tDisplayTextWidth("F", unitFont);
  const int groupW = valueW + 12 + fW;
  const int startX = 94 - groupW / 2;
  const int topY = 112;
  drawTDisplayTextAt(startX, topY, value, C_WHITE, numberFont);
  const int degreeX = startX + valueW + 3;
  gfx->drawCircle(degreeX, topY + 7, 3, C_WHITE);
  drawTDisplayTextAt(degreeX + 7, topY + 13, "F", C_WHITE, unitFont);
}

void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 182, 198);
  const uint16_t cyan = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();
  drawConceptCard(154, 210, 76, 52, 8, true);
  centerBoldText(tomorrow ? "TMRW" : "TODAY", 192, 214, 1, cyan);
  centerBoldText("HI", 173, 226, 1, muted);
  centerBoldText("LO", 211, 226, 1, muted);
  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
  if (wx.forecastValid && isfinite(high) && isfinite(low)) {
    String highText = String((int)lroundf(high));
    String lowText = String((int)lroundf(low));
    const int highW = tDisplayTextWidth(highText, 2);
    const int lowW = tDisplayTextWidth(lowText, 2);
    int highX = 173 - (highW + 7) / 2;
    int lowX = 211 - (lowW + 7) / 2;
    printBoldAt(highX, 238, highText, C_WHITE, 2);
    gfx->drawCircle(highX + highW + 3, 242, 2, C_WHITE);
    printBoldAt(lowX, 238, lowText, C_WHITE, 2);
    gfx->drawCircle(lowX + lowW + 3, 242, 2, C_WHITE);
  } else {
    centerBoldText("--", 173, 238, 2, C_WHITE);
    centerBoldText("--", 211, 238, 2, C_WHITE);
  }
}

void headerText() {
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 16) station = station.substring(0, 16);
  printBoldAt(12, 12, station, C_WHITE, 2);
  rightText(currentDateText(), 229, 18, 1, rgb565(219, 231, 238));
  printBoldAt(12, 34, "CURRENT CONDITIONS", rgb565(157, 184, 202), 1);
  gfx->drawFastHLine(12, 47, 216, rgb565(23, 63, 85));
}

void drawFooter() {
  const uint16_t muted = rgb565(168, 198, 216);
  const uint16_t green = rgb565(117, 237, 79);
  const uint16_t red = rgb565(255, 122, 103);
  gfx->fillRect(0, 267, 240, 53, C_BLACK);
  drawConceptCard(10, 272, 220, 36, 9, true);
  if (WiFi.status() != WL_CONNECTED) {
    centerBoldText(setupApStarted ? "Setup: 192.168.4.1/config" : "Wi-Fi disconnected", 120, 282, 1, C_WHITE);
    return;
  }
  if (!apiConfigured()) {
    centerBoldText("Open /config", 120, 282, 2, C_WHITE);
    return;
  }
  const bool offline = !wx.valid;
  const bool stale = !offline && dataStale();
  const uint16_t stateColor = offline ? red : (stale ? red : green);
  drawClockIcon(23, 290, muted);
  String left;
  String state;
  uint16_t leftColor = C_WHITE;
  int leftX = 36;
  if (offline) {
    left = lastApiError.length() ? "Weather API error" : "Fetching weather...";
    state = "OFFLINE";
    leftColor = lastApiError.length() ? red : C_WHITE;
  } else {
    left = "Updated " + updateClockText();
    state = stale ? "STALE" : "ONLINE";
    leftColor = stale ? red : C_WHITE;
  }
  printBoldAt(leftX, 281, left, leftColor, 2);
  const int stateW = tDisplayTextWidth(state, 2);
  const int stateX = 225 - stateW;
  gfx->fillCircle(stateX - 6, 290, 2, stateColor);
  printBoldAt(stateX, 281, state, stateColor, 2);
}

void drawWaitingScreen() {
  gfx->fillScreen(C_BLACK);
  headerText();
  drawConceptCard(10, 54, 220, 208, 12, true);
  centerBoldText(setupApStarted ? "SETUP" : "WAITING", 120, 118, 4, C_WHITE);
  if (setupApStarted) {
    centerText("Connect to setup Wi-Fi", 120, 166, 2, rgb565(159, 183, 201));
    centerText(setupApName(), 120, 190, 2, rgb565(114, 202, 255));
    centerText("192.168.4.1/config", 120, 214, 2, rgb565(114, 202, 255));
  } else {
    centerText(lastApiError.length() ? "Weather API error" : "Preparing display", 120, 166, 2, rgb565(159, 183, 201));
    if (WiFi.status() != WL_CONNECTED) centerText("Connecting to Wi-Fi...", 120, 195, 2, rgb565(114, 202, 255));
    else if (!apiConfigured()) centerText("API setup needed", 120, 195, 2, rgb565(114, 202, 255));
    else if (lastApiError.length()) centerText("Check provider configuration", 120, 195, 2, rgb565(114, 202, 255));
    else centerText("Fetching weather...", 120, 195, 2, rgb565(114, 202, 255));
  }
  drawFooter();
}

void drawWeatherScreen() {
  gfx->fillScreen(C_BLACK);
  headerText();
  const uint16_t cyan = rgb565(114, 202, 255);
  const uint16_t muted = rgb565(159, 183, 201);
  const uint16_t green = rgb565(123, 220, 71);
  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);
  const bool cold = windChillApplies();
  fillGradientRoundRect(10, 54, 128, 151, 12, risk.panelTop, risk.panelBottom);
  gfx->drawRoundRect(10, 54, 128, 151, 12, risk.border);
  if (cold) drawHeroWind(20, 88); else drawHeroSun(36, 96);
  centerBoldText(apparentTitle(), 94, 66, 2, C_WHITE);
  drawApparentTemperature(apparentF);
  gfx->fillRoundRect(18, 170, 112, 24, 12, risk.status);
  gfx->drawRoundRect(18, 170, 112, 24, 12, risk.accent);
  centerBoldText(apparentRiskLabel(), 74, 174, 2, risk.accent);

  drawConceptCard(143, 54, 87, 34, 7, false);
  drawThermometer(148, 61, rgb565(255, 92, 75));
  printBoldAt(169, 58, "TEMP", cyan, 1);
  printTempValueCompact(169, 70, wx.tempF);
  drawConceptCard(143, 91, 87, 34, 7, false);
  drawDrop(157, 98, rgb565(72, 186, 255));
  printBoldAt(169, 95, "HUMID", cyan, 1);
  printBoldAt(169, 106, String((int)lroundf(wx.humidity)) + "%", C_WHITE, 2);
  drawConceptCard(143, 128, 87, 34, 7, false);
  drawLeaf(157, 145, green);
  printBoldAt(169, 132, "DEW PT", cyan, 1);
  printTempValueCompact(169, 143, wx.dewPointF);
  drawConceptCard(143, 165, 87, 40, 7, false);
  drawTrend(148, 176, cyan);
  printBoldAt(169, 169, "VS YDAY", cyan, 1);
  printSignedTempValueCompact(169, 181, wx.fromYesterdayF);

  drawConceptCard(10, 210, 68, 52, 8, true);
  centerBoldText("WIND", 44, 213, 1, rgb565(157, 200, 228));
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 44, 225, 2, C_WHITE);
  centerBoldText("MPH", 44, 242, 1, muted);
  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"), 44, 251, 1, rgb565(166, 209, 234));

  drawConceptCard(82, 210, 68, 52, 8, true);
  centerBoldText("DIR", 116, 213, 1, rgb565(157, 200, 228));
  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg));
    const int dirW = tDisplayTextWidth(dirNumber, 2);
    const int dirX = 116 - (dirW + 7) / 2;
    printBoldAt(dirX, 225, dirNumber, C_WHITE, 2);
    gfx->drawCircle(dirX + dirW + 3, 229, 2, C_WHITE);
  } else centerBoldText("--", 116, 225, 2, C_WHITE);
  centerBoldText(isfinite(wx.windDirDeg) ? directionText(wx.windDirDeg) : "--", 116, 246, 1, rgb565(157, 200, 228));
  drawForecastHighLowCard();
  drawFooter();
}

'''
s = s[:START28] + TAIL28 + s[END28:]
P28.write_text(s)

# ---------------- 7C display ----------------
s = P7.read_text()
s = s.replace('#include <Arduino_GFX_Library.h>\n', '#include <Arduino_GFX_Library.h>\n#include <LovyanGFX.hpp>\n')
s = between(s, 'static void setText(uint16_t color, uint8_t size)', 'static void drawConceptCard', ADAPTER + PRINT_HELPERS)

START7 = s.index('static void drawMetricCardValue')
END7 = s.index('void displayBegin()', START7)
TAIL7 = r'''static void drawMetricCardValue(int x, int y, int w, int h, const uint16_t *iconData,
                                const String &label, const String &value, uint8_t valueSize = 3) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 12, false);
  drawIconBitmapScaled(x + 12, y + (h - 40) / 2, iconData, 2);
  printBoldAt(x + 64, y + 8, label, cyan, 1);
  printBoldAt(x + 64, y + 25, value, C_WHITE, valueSize);
}

static void drawMetricCardTemperatureValue(int x, int y, int w, int h,
                                           const uint16_t *iconData,
                                           const String &label, float value,
                                           bool signedValue = false) {
  const uint16_t cyan = rgb565(114, 202, 255);
  drawConceptCard(x, y, w, h, 12, false);
  drawIconBitmapScaled(x + 12, y + (h - 40) / 2, iconData, 2);
  printBoldAt(x + 64, y + 8, label, cyan, 1);
  if (!isfinite(value)) {
    printBoldAt(x + 64, y + 25, "--", C_WHITE, 3);
    return;
  }
  String number;
  if (signedValue && value >= 0.0f) number += "+";
  number += String(value, 1);
  const int numberW = tDisplayTextWidth(number, 3);
  const int valueX = x + 64;
  const int valueY = y + 25;
  printBoldAt(valueX, valueY, number, C_WHITE, 3);
  gfx->drawCircle(valueX + numberW + 4, valueY + 4, 2, C_WHITE);
  printBoldAt(valueX + numberW + 9, valueY, "F", C_WHITE, 2);
}

static void drawApparentTemperature(float apparentF) {
  const String value = String((int)lroundf(apparentF));
  const lgfx::IFont *numberFont = &fonts::Font7;
  const lgfx::IFont *unitFont = &fonts::Font4;
  const int valueW = tDisplayTextWidth(value, numberFont);
  const int fW = tDisplayTextWidth("F", unitFont);
  const int groupW = valueW + 13 + fW;
  const int startX = 320 - groupW / 2;
  const int topY = 143;
  drawTDisplayTextAt(startX, topY, value, C_WHITE, numberFont);
  const int degreeX = startX + valueW + 3;
  gfx->drawCircle(degreeX, topY + 7, 3, C_WHITE);
  drawTDisplayTextAt(degreeX + 8, topY + 13, "F", C_WHITE, unitFont);
}

void drawForecastHighLowCard() {
  const uint16_t muted = rgb565(157, 182, 198), cyan = rgb565(157, 200, 228);
  const bool tomorrow = forecastShowsTomorrow();
  drawConceptCard(477, 316, 290, 76, 14, true);
  drawIconBitmapScaled(493, 335, ICON_SUN, 2);
  centerBoldText(tomorrow ? "TOMORROW" : "TODAY", 620, 322, 1, cyan);
  centerBoldText("HIGH", 580, 338, 1, muted);
  centerBoldText("LOW", 680, 338, 1, muted);
  float high = tomorrow ? wx.forecastTomorrowHighF : wx.forecastTodayHighF;
  float low = tomorrow ? wx.forecastTomorrowLowF : wx.forecastTodayLowF;
  if (wx.forecastValid && isfinite(high) && isfinite(low)) {
    String highText = String((int)lroundf(high));
    String lowText = String((int)lroundf(low));
    const int highW = tDisplayTextWidth(highText, 2);
    const int lowW = tDisplayTextWidth(lowText, 2);
    int hx = 580 - (highW + 8) / 2;
    int lx = 680 - (lowW + 8) / 2;
    printBoldAt(hx, 354, highText, C_WHITE, 2);
    gfx->drawCircle(hx + highW + 3, 358, 2, C_WHITE);
    printBoldAt(lx, 354, lowText, C_WHITE, 2);
    gfx->drawCircle(lx + lowW + 3, 358, 2, C_WHITE);
  } else {
    centerBoldText("--", 580, 354, 2, C_WHITE);
    centerBoldText("--", 680, 354, 2, C_WHITE);
  }
}

static void drawHeader() {
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 20) station = station.substring(0, 20);
  printBoldAt(30, 20, station, C_WHITE, 2);
  rightText(currentDateText(), 770, 27, 1, rgb565(219, 231, 238));
  printBoldAt(30, 56, "CURRENT CONDITIONS", rgb565(157, 184, 202), 1);
  gfx->drawFastHLine(30, 76, 740, rgb565(23, 63, 85));
}

void drawFooter() {
  const uint16_t muted = rgb565(168, 198, 216), green = rgb565(117, 237, 79), red = rgb565(255, 122, 103);
  gfx->fillRect(0, 400, LCD_WIDTH, 80, C_BLACK);
  drawConceptCard(33, 410, 734, 52, 14, true);
  if (WiFi.status() != WL_CONNECTED) {
    centerBoldText(setupApStarted ? "Setup: 192.168.4.1/config" : "Wi-Fi disconnected", 400, 425, 2, C_WHITE); return;
  }
  if (!apiConfigured()) { centerBoldText("Open /config", 400, 425, 2, C_WHITE); return; }
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
    left = "Updated " + updateClockText();
    state = stale ? "STALE" : "ONLINE";
    leftColor = stale ? red : C_WHITE;
  }
  printBoldAt(94, 425, left, leftColor, 2);
  gfx->drawFastVLine(570, 419, 34, rgb565(85, 115, 133));
  gfx->fillCircle(649, 436, 5, stateColor);
  printBoldAt(662, 425, state, stateColor, 2);
}

void drawWaitingScreen() {
  gfx->fillScreen(C_BLACK);
  drawHeader();
  drawConceptCard(33, 82, 734, 310, 18, true);
  centerBoldText(setupApStarted ? "SETUP" : "WAITING", 400, 164, 4, C_WHITE);
  if (setupApStarted) {
    centerBoldText("Connect to setup Wi-Fi", 400, 233, 2, rgb565(159, 183, 201));
    centerBoldText(setupApName(), 400, 281, 2, rgb565(114, 202, 255));
    centerBoldText("192.168.4.1/config", 400, 311, 2, rgb565(114, 202, 255));
  } else {
    centerBoldText(lastApiError.length() ? "Weather API error" : "Preparing display", 400, 233, 2, rgb565(159, 183, 201));
    if (WiFi.status() != WL_CONNECTED) centerBoldText("Connecting to Wi-Fi...", 400, 281, 2, rgb565(114, 202, 255));
    else if (!apiConfigured()) centerBoldText("API setup needed", 400, 281, 2, rgb565(114, 202, 255));
    else if (lastApiError.length()) centerBoldText("Check provider configuration", 400, 281, 2, rgb565(114, 202, 255));
    else centerBoldText("Fetching weather...", 400, 281, 2, rgb565(114, 202, 255));
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
  centerBoldText(apparentTitle(), 325, 103, 2, C_WHITE);
  drawApparentTemperature(apparentF);
  gfx->fillRoundRect(60, 260, 373, 34, 17, risk.status);
  gfx->drawRoundRect(60, 260, 373, 34, 17, risk.accent);
  centerBoldText(apparentRiskLabel(), 246, 268, 2, risk.accent);

  drawMetricCardTemperatureValue(477, 82, 290, 50, ICON_THERMOMETER, "TEMP", wx.tempF);
  drawMetricCardValue(477, 137, 290, 50, ICON_DROP, "HUMIDITY", isfinite(wx.humidity) ? String((int)lroundf(wx.humidity)) + "%" : "--");
  drawMetricCardTemperatureValue(477, 192, 290, 50, ICON_LEAF, "DEW POINT", wx.dewPointF);
  drawMetricCardTemperatureValue(477, 247, 290, 60, ICON_TREND, "FROM YDAY", wx.fromYesterdayF, true);

  drawConceptCard(33, 316, 207, 76, 14, true);
  drawIconBitmapScaled(48, 337, ICON_WIND, 2);
  centerBoldText("WIND", 136, 322, 1, rgb565(157, 200, 228));
  centerBoldText(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--", 160, 342, 2, C_WHITE);
  centerBoldText("mph", 160, 365, 1, muted);
  centerBoldText(String("GUST ") + (isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--"), 136, 378, 1, rgb565(166, 209, 234));

  drawConceptCard(253, 316, 207, 76, 14, true);
  drawIconBitmapScaled(270, 337, ICON_COMPASS, 2);
  centerBoldText("DIRECTION", 356, 322, 1, rgb565(157, 200, 228));
  if (isfinite(wx.windDirDeg)) {
    String dirNumber = String((int)lroundf(wx.windDirDeg));
    const int dirW = tDisplayTextWidth(dirNumber, 2);
    const int startX = 385 - (dirW + 8) / 2;
    printBoldAt(startX, 342, dirNumber, C_WHITE, 2);
    gfx->drawCircle(startX + dirW + 3, 346, 2, C_WHITE);
    centerBoldText(directionText(wx.windDirDeg), 356, 370, 1, rgb565(157, 200, 228));
  } else {
    centerBoldText("--", 385, 342, 2, C_WHITE);
    centerBoldText("--", 356, 370, 1, rgb565(157, 200, 228));
  }
  drawForecastHighLowCard();
  drawFooter();
}

'''
s = s[:START7] + TAIL7 + s[END7:]
P7.write_text(s)

for ini in (INI28, INI7):
    t = ini.read_text()
    if 'lovyan03/LovyanGFX@1.2.7' not in t:
        t = t.replace('lib_deps =\n', 'lib_deps =\n    lovyan03/LovyanGFX@1.2.7\n', 1)
    ini.write_text(t)

# Basic contract checks.
assert '#include <LovyanGFX.hpp>' in P28.read_text()
assert '#include <LovyanGFX.hpp>' in P7.read_text()
assert 'fonts::Font0' in P28.read_text() and 'fonts::Font7' in P28.read_text()
assert 'fonts::Font0' in P7.read_text() and 'fonts::Font7' in P7.read_text()
assert 'FreeSans8pt7b' not in P28.read_text()
print('Applied exact T-Display font family and size tiers to both Waveshare targets')
