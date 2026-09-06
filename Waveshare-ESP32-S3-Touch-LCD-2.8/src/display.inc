  delay(20);
}

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

void drawWiFiIcon(int x, int y, uint16_t color) {
  gfx->drawCircle(x, y, 2, color);
  gfx->drawArc(x, y, 14, 14, 220, 320, color);
  gfx->drawArc(x, y, 10, 10, 220, 320, color);
  gfx->drawArc(x, y, 6, 6, 220, 320, color);
}

void drawThermometer(int x, int y, uint16_t color) {
  gfx->drawRoundRect(x, y, 10, 30, 5, color);
  gfx->fillCircle(x + 5, y + 30, 7, color);
  gfx->fillRect(x + 4, y + 10, 3, 20, color);
}

void drawDrop(int x, int y, uint16_t color) {
  gfx->fillTriangle(x, y, x - 9, y + 18, x + 9, y + 18, color);
  gfx->fillCircle(x, y + 18, 9, color);
}

void drawLeaf(int x, int y, uint16_t color) {
  gfx->drawCircle(x, y, 9, color);
  gfx->drawLine(x - 6, y + 6, x + 7, y - 7, color);
  gfx->drawLine(x + 1, y + 1, x + 8, y + 8, color);
}

void drawTrend(int x, int y, uint16_t color) {
  gfx->drawLine(x, y + 16, x, y, color);
  gfx->drawLine(x, y + 16, x + 18, y + 16, color);
  gfx->drawLine(x + 2, y + 12, x + 7, y + 8, color);
  gfx->drawLine(x + 7, y + 8, x + 12, y + 10, color);
  gfx->drawLine(x + 12, y + 10, x + 18, y + 2, color);
  gfx->drawLine(x + 14, y + 2, x + 18, y + 2, color);
  gfx->drawLine(x + 18, y + 2, x + 18, y + 6, color);
}

void drawWindIcon(int x, int y, uint16_t color) {
  gfx->drawLine(x, y, x + 18, y, color);
  gfx->drawLine(x + 11, y - 4, x + 18, y, color);
  gfx->drawLine(x + 11, y + 4, x + 18, y, color);
  gfx->drawLine(x, y + 9, x + 24, y + 9, color);
  gfx->drawLine(x + 17, y + 5, x + 24, y + 9, color);
  gfx->drawLine(x + 17, y + 13, x + 24, y + 9, color);
}

void drawCompassIcon(int x, int y, uint16_t color) {
  gfx->drawCircle(x, y, 12, color);
  gfx->drawLine(x, y + 9, x, y - 9, color);
  gfx->drawLine(x, y - 9, x - 5, y + 2, color);
  gfx->drawLine(x, y - 9, x + 5, y + 2, color);
}

void drawRoundedRectCard(int x, int y, int w, int h) {
  uint16_t bg = rgb565(2, 25, 43);
  uint16_t border = rgb565(10, 63, 100);
  gfx->fillRoundRect(x, y, w, h, 8, bg);
  gfx->drawRoundRect(x, y, w, h, 8, border);
}

void drawSunIcon(int x, int y, uint16_t color) {
  gfx->fillCircle(x, y, 7, color);
  gfx->drawLine(x, y - 13, x, y - 10, color);
  gfx->drawLine(x, y + 10, x, y + 13, color);
  gfx->drawLine(x - 13, y, x - 10, y, color);
  gfx->drawLine(x + 10, y, x + 13, y, color);
  gfx->drawLine(x - 9, y - 9, x - 7, y - 7, color);
  gfx->drawLine(x + 7, y + 7, x + 9, y + 9, color);
  gfx->drawLine(x - 9, y + 9, x - 7, y + 7, color);
  gfx->drawLine(x + 7, y - 7, x + 9, y - 9, color);
}

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
  s += "F";
  return s;
}

void headerText() {
  const uint16_t cyan = rgb565(65, 205, 255);

  setText(C_WHITE, 2);
  gfx->setCursor(14, 17);
  String station = cfg.stationName.length() ? cfg.stationName : "Weather Station";
  if (station.length() > 16) station = station.substring(0, 16);
  gfx->print(station);

  // Keep the calendar date, but no standalone live/current time. The footer
  // retains the observation/update timestamp.
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
    gfx->print(lastApiError.length() ? "Ambient API error" : "Fetching Ambient...");
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
    centerText(apiConfigured() ? "AmbientWeather.net" : "API setup needed", 120, 178, 2, rgb565(175, 182, 192));
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

  const uint16_t cyan = rgb565(65, 205, 255);
  const uint16_t cardBg = rgb565(2, 25, 43);
  const uint16_t green = rgb565(120, 225, 70);
  const uint16_t yellow = rgb565(255, 195, 25);

  float apparentF = apparentOutdoorF();
  RiskStyle risk = riskFor(apparentF);

  // Large left apparent-temperature panel.
  gfx->fillRoundRect(10, 65, 128, 128, 12, risk.panel);
  centerText(apparentTitle(), 74, 78, 2, C_WHITE);

  String value = String(apparentF, 1);
  setText(C_WHITE, 5);
  int16_t x1, y1;
  uint16_t w, h;
  gfx->getTextBounds(value, 0, 0, &x1, &y1, &w, &h);
  int valX = 72 - (int)w / 2;
  gfx->setCursor(valX, 105);
  gfx->print(value);
  gfx->drawCircle(valX + w + 5, 106, 3, C_WHITE);

  setText(C_WHITE, 2);
  gfx->setCursor(valX + w + 12, 119);
  gfx->print("F");

  gfx->fillRoundRect(22, 154, 104, 25, 7, risk.status);
  centerText(apparentRiskLabel(), 74, 161, 2, C_WHITE);

  // Four stacked right-side mockup cards.
  drawRoundedRectCard(143, 65, 87, 29);
  drawThermometer(150, 68, rgb565(255, 70, 55));
  setText(C_WHITE, 2);
  gfx->setCursor(170, 69);
  gfx->print(String(wx.tempF, 1));
  gfx->print("F");
  setText(cyan, 1);
  gfx->setCursor(170, 85);
  gfx->print("Outdoor Temp");

  drawRoundedRectCard(143, 98, 87, 29);
  drawDrop(158, 101, rgb565(50, 165, 255));
  setText(C_WHITE, 2);
  gfx->setCursor(170, 102);
  gfx->print(String((int)lroundf(wx.humidity)));
  gfx->print("%");
  setText(cyan, 1);
  gfx->setCursor(170, 118);
  gfx->print("Rel. Humidity");

  drawRoundedRectCard(143, 131, 87, 29);
  drawLeaf(157, 145, green);
  setText(C_WHITE, 2);
  gfx->setCursor(170, 135);
  gfx->print(isfinite(wx.dewPointF) ? String(wx.dewPointF, 1) + "F" : "--");
  setText(cyan, 1);
  gfx->setCursor(170, 151);
  gfx->print("Dew Point");

  drawRoundedRectCard(143, 164, 87, 29);
  drawTrend(149, 170, cyan);
  setText(C_WHITE, 2);
  gfx->setCursor(170, 168);
  gfx->print(signedTempDelta(wx.fromYesterdayF));
  setText(cyan, 1);
  gfx->setCursor(170, 184);
  gfx->print("From Yesterday");

  // Bottom mockup cards.
  //
  // Wind + Direction now split the exact 128-pixel width of the large
  // apparent-temperature panel (x=10..137) into two equal 62-pixel cards
  // separated by a 4-pixel gutter.
  drawRoundedRectCard(10, 201, 62, 68);
  drawWindIcon(16, 216, cyan);
  setText(C_WHITE, 2);
  gfx->setCursor(34, 211);
  gfx->print(isfinite(wx.windMph) ? String(wx.windMph, 1) : "--");
  setText(cyan, 1);
  gfx->setCursor(17, 237);
  gfx->print("mph  Gust ");
  gfx->print(isfinite(wx.gustMph) ? String(wx.gustMph, 1) : "--");
  gfx->setCursor(17, 252);
  gfx->print("Max ");
  gfx->print(isfinite(wx.maxDailyGustMph) ? String(wx.maxDailyGustMph, 1) : "--");

  drawRoundedRectCard(76, 201, 62, 68);
  drawCompassIcon(92, 228, cyan);
  setText(C_WHITE, 2);
  gfx->setCursor(106, 211);
  if (isfinite(wx.windDirDeg)) {
    gfx->print((int)lroundf(wx.windDirDeg));
    gfx->print((char)247);
  } else {
    gfx->print("--");
  }
  setText(cyan, 1);
  gfx->setCursor(106, 234);
  String dirLong = directionLongText(wx.windDirDeg);
  if (dirLong.length() > 7) dirLong = directionText(wx.windDirDeg);
  gfx->print(dirLong);

  // Today's High / Low is aligned to the right-side metric column above:
  // same x position and width as Temperature/Humidity/Dew Point/Yesterday.
  drawRoundedRectCard(143, 201, 87, 68);
  drawSunIcon(158, 228, yellow);
  setText(C_WHITE, 1);
  gfx->setCursor(174, 211);
  if (wx.summaryValid) {
    gfx->print(String(wx.todayHighF, 1));
    gfx->print(" / ");
    gfx->print(String(wx.todayLowF, 1));
    gfx->print("F");
  } else {
    gfx->print("-- / --");
  }
  setText(cyan, 1);
  gfx->setCursor(174, 231);
  gfx->print("Today's");
  gfx->setCursor(174, 244);
  gfx->print("High / Low");

  drawFooter();
}


void setup() {
  Serial.begin(115200);
  delay(250);
  pinMode(LCD_BL, OUTPUT);
  digitalWrite(LCD_BL, HIGH);
  gfx->begin();
  gfx->fillScreen(C_BLACK);
  drawWaitingScreen();
  commonSetup();
  lastFooterStateKey = footerStateKey();
}

void loop() {
  commonLoop();
}
