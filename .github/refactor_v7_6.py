from pathlib import Path
import re, shutil

OUT_ROOT = Path('.')
SRC_ROOT = OUT_ROOT
TD_SRC = (OUT_ROOT/'T-Display-S3/src/main.cpp').read_text()
WV_SRC = (OUT_ROOT/'Waveshare-ESP32-S3-Touch-LCD-2.8/src/main.cpp').read_text()
COMMON_SRC = TD_SRC

# --- helpers ---
def extract_function(src: str, name: str) -> str:
    # Find a definition at line start containing name(...){, not a declaration.
    pat = re.compile(r'(?m)^[^\n;]*\b' + re.escape(name) + r'\s*\([^;\n]*\)\s*\{')
    m = pat.search(src)
    if not m:
        raise RuntimeError(f'Function not found: {name}')
    start = m.start()
    brace = src.find('{', m.start(), m.end())
    depth = 0
    i = brace
    in_str = None
    escape = False
    while i < len(src):
        ch = src[i]
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == in_str:
                in_str = None
        else:
            if ch in ('"', "'"):
                in_str = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    while end < len(src) and src[end] in ' \t': end += 1
                    if end < len(src) and src[end] == '\n': end += 1
                    if end < len(src) and src[end] == '\n': end += 1
                    return src[start:end].rstrip() + '\n'
        i += 1
    raise RuntimeError(f'Unbalanced function: {name}')

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + '\n', encoding='utf-8')

weather_funcs = [
    'dewPointFromTempHumidityF','nwsHeatIndexF','nwsWindChillF','windChillApplies',
    'apparentOutdoorF','apparentTitle','riskLabel','coldRiskLabel','apparentRiskLabel','directionText'
]
config_funcs = ['normalizeMac','applyCompileTimeDefaults','loadConfig','saveConfig','apiConfigured']
time_funcs = ['observationAgeSeconds','dataStale','formatClockFromEpoch','formatDateFromEpoch','wxEpochSeconds','updateClockText','currentDateText']
ambient_funcs = ['tryField','fetchAmbientDevices','applySelectedDevice','sameLocalDay','respectAmbientRateLimit','fetchAmbientSummary','pollAmbient']
web_funcs = ['htmlEscape','pageHead','pageTail','handleRoot','handleConfig','handleSave','handleClearAmbient','handleFactoryReset','handlePollNow','handleDiscover','handleSelect','jsonStatus','startWebServer']
wifi_funcs = ['currentIp','setupApName','startSetupAp','connectWifi']
ui_state_funcs = ['floatDifferent','weatherDisplayChanged','footerStateKey']
controller_funcs = ['commonSetup','commonLoop']

url_encode = extract_function(COMMON_SRC, 'urlEncode')

app_state_h = r'''#pragma once
#include <Arduino.h>
#include <WebServer.h>
#include <Preferences.h>
#include "config.h"

struct AppConfig {
  String ssid;
  String wifiPassword;
  String applicationKey;
  String apiKey;
  String macAddress;
  String stationName;
  String hostname = DEFAULT_HOSTNAME;
  String timezoneTz = DEFAULT_TIMEZONE_TZ;
  uint32_t pollSeconds = DEFAULT_POLL_SECONDS;
  uint32_t staleSeconds = DEFAULT_STALE_SECONDS;
};

struct WeatherData {
  float tempF = NAN;
  float humidity = NAN;
  float heatIndexF = NAN;
  float dewPointF = NAN;
  float windMph = NAN;
  float gustMph = NAN;
  float maxDailyGustMph = NAN;
  float windChillF = NAN;
  float windDirDeg = NAN;
  float yesterdayTempF = NAN;
  float fromYesterdayF = NAN;
  float todayHighF = NAN;
  float todayLowF = NAN;
  uint64_t dateUtcMs = 0;
  unsigned long fetchedMs = 0;
  unsigned long summaryFetchedMs = 0;
  bool summaryValid = false;
  bool valid = false;
};

extern WebServer server;
extern Preferences prefs;
extern AppConfig cfg;
extern WeatherData wx;

extern bool webStarted;
extern bool setupApStarted;
extern unsigned long lastWifiAttemptMs;
extern unsigned long lastPollMs;
extern unsigned long lastSummaryPollMs;
extern unsigned long lastAmbientRequestMs;
extern unsigned long lastUiStateCheckMs;
extern String lastFooterStateKey;
extern String lastApiError;
extern int lastHttpCode;
extern int lastSummaryHttpCode;
extern String lastSummaryError;
'''

app_state_cpp = r'''#include "app_state.h"

WebServer server(80);
Preferences prefs;
AppConfig cfg;
WeatherData wx;

bool webStarted = false;
bool setupApStarted = false;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastPollMs = 0;
unsigned long lastSummaryPollMs = 0;
unsigned long lastAmbientRequestMs = 0;
unsigned long lastUiStateCheckMs = 0;
String lastFooterStateKey;
String lastApiError;
int lastHttpCode = 0;
int lastSummaryHttpCode = 0;
String lastSummaryError;
'''

weather_h = r'''#pragma once
#include <Arduino.h>

float dewPointFromTempHumidityF(float tF, float rh);
float nwsHeatIndexF(float t, float rh);
float nwsWindChillF(float t, float windMph);
bool windChillApplies();
float apparentOutdoorF();
const char* apparentTitle();
const char* riskLabel(float hi);
const char* coldRiskLabel(float wc);
const char* apparentRiskLabel();
String directionText(float deg);
'''
weather_cpp = '#include <math.h>\n#include "app_state.h"\n#include "weather_math.h"\n\n' + '\n'.join(extract_function(COMMON_SRC,n) for n in weather_funcs)

config_h = r'''#pragma once
#include <Arduino.h>

String normalizeMac(String mac);
void applyCompileTimeDefaults();
void loadConfig();
void saveConfig();
bool apiConfigured();
'''
config_cpp = '#include "app_state.h"\n#include "config_store.h"\n#include "compile_defaults.h"\n\n' + '\n'.join(extract_function(COMMON_SRC,n) for n in config_funcs)

time_h = r'''#pragma once
#include <Arduino.h>
#include <time.h>

uint32_t observationAgeSeconds();
bool dataStale();
String formatClockFromEpoch(time_t t);
String formatDateFromEpoch(time_t t);
time_t wxEpochSeconds();
String updateClockText();
String currentDateText();
'''
time_cpp = '#include <time.h>\n#include "app_state.h"\n#include "time_utils.h"\n\n' + '\n'.join(extract_function(COMMON_SRC,n) for n in time_funcs)

ambient_h = r'''#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

bool fetchAmbientDevices(DynamicJsonDocument &doc, String &errorOut);
bool applySelectedDevice(JsonArray devices, bool allowAutoSelect, String &errorOut);
bool fetchAmbientSummary(String &errorOut);
bool pollAmbient(bool forceRedraw = true);
'''
ambient_cpp = '''#include <WiFi.h>\n#include <HTTPClient.h>\n#include <WiFiClientSecure.h>\n#include <ArduinoJson.h>\n#include <time.h>\n#include <math.h>\n#include "app_state.h"\n#include "ambient_weather.h"\n#include "config_store.h"\n#include "display_ui.h"\n#include "ui_state.h"\n#include "weather_math.h"\n#include "config.h"\n\n''' + url_encode + '\n' + '\n'.join(extract_function(COMMON_SRC,n) for n in ambient_funcs)

web_h = r'''#pragma once
#include <Arduino.h>

String jsonStatus();
void startWebServer();
'''
web_cpp = '''#include <WiFi.h>\n#include <ArduinoJson.h>\n#include "app_state.h"\n#include "web_ui.h"\n#include "ambient_weather.h"\n#include "config_store.h"\n#include "display_ui.h"\n#include "time_utils.h"\n#include "weather_math.h"\n#include "wifi_manager.h"\n\n''' + '\n'.join(extract_function(COMMON_SRC,n) for n in web_funcs)

wifi_h = r'''#pragma once
#include <Arduino.h>

String currentIp();
String setupApName();
void startSetupAp();
bool connectWifi();
'''
wifi_cpp = '''#include <WiFi.h>\n#include <time.h>\n#include "app_state.h"\n#include "wifi_manager.h"\n#include "config.h"\n#include "display_ui.h"\n#include "web_ui.h"\n\n''' + '\n'.join(extract_function(COMMON_SRC,n) for n in wifi_funcs)

ui_state_h = r'''#pragma once
#include <Arduino.h>
#include "app_state.h"

bool weatherDisplayChanged(const WeatherData &before, const WeatherData &after);
String footerStateKey();
'''
ui_state_cpp = '''#include <WiFi.h>\n#include <math.h>\n#include "app_state.h"\n#include "ui_state.h"\n#include "config_store.h"\n#include "time_utils.h"\n\n''' + '\n'.join(extract_function(COMMON_SRC,n) for n in ui_state_funcs)
ui_state_cpp = ui_state_cpp.replace('static bool weatherDisplayChanged', 'bool weatherDisplayChanged', 1)

controller_h = r'''#pragma once

void appSetup();
void appLoop();
'''
controller_cpp_body = '\n'.join(extract_function(COMMON_SRC,n) for n in controller_funcs)
controller_cpp_body = controller_cpp_body.replace('void commonSetup()', 'void appSetup()', 1).replace('void commonLoop()', 'void appLoop()', 1)
controller_cpp = '''#include <WiFi.h>\n#include "app_state.h"\n#include "app_controller.h"\n#include "ambient_weather.h"\n#include "config_store.h"\n#include "display_ui.h"\n#include "ui_state.h"\n#include "web_ui.h"\n#include "wifi_manager.h"\n#include "config.h"\n\n''' + controller_cpp_body

display_h = r'''#pragma once

void displayBegin();
void drawWaitingScreen();
void drawWeatherScreen();
void drawFooter();
'''

main_cpp = r'''#include <Arduino.h>
#include "app_controller.h"
#include "app_state.h"
#include "display_ui.h"
#include "ui_state.h"

void setup() {
  Serial.begin(115200);
  delay(250);

  displayBegin();
  drawWaitingScreen();
  appSetup();
  lastFooterStateKey = footerStateKey();
}

void loop() {
  appLoop();
}
'''

def display_module(src: str, marker: str, board: str) -> str:
    start = src.index(marker)
    setup_start = src.index('\nvoid setup()', start)
    body = src[start:setup_start].strip() + '\n\n'
    pre = '''#include <Arduino.h>\n#include <WiFi.h>\n#include <math.h>\n#include "app_state.h"\n#include "config_store.h"\n#include "display_ui.h"\n#include "time_utils.h"\n#include "weather_math.h"\n#include "wifi_manager.h"\n#include "ui_assets.h"\n\n'''
    if board == 'td':
        begin = '''void displayBegin() {\n  display.init();\n  display.setRotation(0);\n  display.setBrightness(255);\n  display.fillScreen(C_BLACK);\n}\n'''
    else:
        begin = '''void displayBegin() {\n  pinMode(LCD_BL, OUTPUT);\n  digitalWrite(LCD_BL, HIGH);\n  gfx->begin();\n  gfx->fillScreen(C_BLACK);\n}\n'''
    return pre + body + begin

td_display = display_module(TD_SRC, '#include <LovyanGFX.hpp>', 'td')
wv_display = display_module(WV_SRC, '#include <Arduino_GFX_Library.h>', 'wv')

for board_name, display_cpp in [
    ('T-Display-S3', td_display),
    ('Waveshare-ESP32-S3-Touch-LCD-2.8', wv_display),
]:
    board = OUT_ROOT/board_name
    write(board/'src/main.cpp', main_cpp)
    files = {
        'include/app_state.h': app_state_h,
        'src/app_state.cpp': app_state_cpp,
        'include/weather_math.h': weather_h,
        'src/weather_math.cpp': weather_cpp,
        'include/config_store.h': config_h,
        'src/config_store.cpp': config_cpp,
        'include/time_utils.h': time_h,
        'src/time_utils.cpp': time_cpp,
        'include/ambient_weather.h': ambient_h,
        'src/ambient_weather.cpp': ambient_cpp,
        'include/web_ui.h': web_h,
        'src/web_ui.cpp': web_cpp,
        'include/wifi_manager.h': wifi_h,
        'src/wifi_manager.cpp': wifi_cpp,
        'include/ui_state.h': ui_state_h,
        'src/ui_state.cpp': ui_state_cpp,
        'include/app_controller.h': controller_h,
        'src/app_controller.cpp': controller_cpp,
        'include/display_ui.h': display_h,
        'src/display_ui.cpp': display_cpp,
    }
    for rel, content in files.items():
        write(board/rel, content)

arch = '''# Firmware architecture

Both production targets use the same functional module boundaries. The only
board-specific implementation is `src/display_ui.cpp`.

| Module | Responsibility |
| --- | --- |
| `main.cpp` | Arduino entry points only |
| `app_state.*` | Shared configuration/weather/runtime state |
| `app_controller.*` | Startup and main-loop orchestration |
| `config_store.*` | Preferences/NVS persistence and compile-default migration |
| `weather_math.*` | Heat index, wind chill, dew point, risk labels and wind direction |
| `ambient_weather.*` | AmbientWeather REST polling, JSON parsing, history summary and rate limiting |
| `time_utils.*` | Observation age, stale detection and date/time formatting |
| `wifi_manager.*` | Wi-Fi STA/AP connection and setup-AP behavior |
| `web_ui.*` | Configuration/status HTTP routes and HTML UI |
| `ui_state.*` | Redraw/change detection and footer state key |
| `display_ui.*` | Board-specific display driver, icons and approved production layout |
| `ui_assets.h` | Fixed RGB565 icon assets |

The refactor intentionally preserves the existing behavior and approved V7.5
screen geometry. It replaces the single large translation unit with normal C++
headers and source files; no `.inc` fragments are used.
'''
write(OUT_ROOT/'ARCHITECTURE.md', arch)

release = '''# Production Release V7.6 — modular source refactor

V7.6 restructures both production projects into normal C++ modules grouped by
functional responsibility. The refactor is intended to be behavior-preserving:
weather calculations, AmbientWeather API behavior, persistent configuration,
Wi-Fi/setup AP behavior, icon assets, and approved display geometry remain the
same as V7.5.1.

The previous monolithic `src/main.cpp` is now a small Arduino entry point.
Functional code is separated into `app_state`, `app_controller`,
`config_store`, `weather_math`, `ambient_weather`, `time_utils`,
`wifi_manager`, `web_ui`, `ui_state`, and board-specific `display_ui` modules.

This structure also prevents display helpers such as wind-direction formatting
from being accidentally removed when icon/rendering code changes.
'''
write(OUT_ROOT/'RELEASE_V7_6_MODULAR_REFACTOR.md', release)

readme = (OUT_ROOT/'README.md').read_text()
if '## Production Release V7.6' not in readme:
    readme += '\n\n## Production Release V7.6\n\nBoth board projects are now split into normal `.cpp`/`.h` modules by functional area. See `ARCHITECTURE.md` and `RELEASE_V7_6_MODULAR_REFACTOR.md`.\n'
write(OUT_ROOT/'README.md', readme)

workflow = '''name: Build firmware

on:
  push:
    branches: [main, refactor-modular]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  platformio:
    name: PlatformIO - ${{ matrix.project }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        project:
          - T-Display-S3
          - Waveshare-ESP32-S3-Touch-LCD-2.8
    steps:
      - name: Checkout
        uses: actions/checkout@v7

      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: '3.13'
          cache: pip

      - name: Install PlatformIO
        run: python -m pip install --upgrade platformio

      - name: Build ${{ matrix.project }}
        working-directory: ${{ matrix.project }}
        run: platformio run
'''
write(OUT_ROOT/'.github/workflows/build.yml', workflow)

for board_name in ['T-Display-S3','Waveshare-ESP32-S3-Touch-LCD-2.8']:
    board=OUT_ROOT/board_name
    assert (board/'src/main.cpp').read_text().count('void setup()') == 1
    assert 'pollAmbient' not in (board/'src/main.cpp').read_text()
    assert (board/'src/ambient_weather.cpp').read_text().count('bool pollAmbient') == 1
    assert (board/'src/web_ui.cpp').read_text().count('void startWebServer') == 1
    assert (board/'src/display_ui.cpp').read_text().count('void drawWeatherScreen') == 1
    assert (board/'src/display_ui.cpp').read_text().count('void displayBegin') == 1
    assert not list(board.rglob('*.inc'))
    for h in board.glob('include/*.h'):
        if h.name in ('config.h','compile_defaults.h','ui_assets.h'):
            continue
        assert h.read_text().startswith('#pragma once')

common_files = [
 'src/main.cpp','src/app_state.cpp','src/weather_math.cpp','src/config_store.cpp','src/time_utils.cpp',
 'src/ambient_weather.cpp','src/web_ui.cpp','src/wifi_manager.cpp','src/ui_state.cpp','src/app_controller.cpp',
 'include/app_state.h','include/weather_math.h','include/config_store.h','include/time_utils.h','include/ambient_weather.h',
 'include/web_ui.h','include/wifi_manager.h','include/ui_state.h','include/app_controller.h','include/display_ui.h'
]
for rel in common_files:
    a=(OUT_ROOT/'T-Display-S3'/rel).read_bytes()
    b=(OUT_ROOT/'Waveshare-ESP32-S3-Touch-LCD-2.8'/rel).read_bytes()
    assert a==b, rel

td=(OUT_ROOT/'T-Display-S3/src/display_ui.cpp').read_text()
wv=(OUT_ROOT/'Waveshare-ESP32-S3-Touch-LCD-2.8/src/display_ui.cpp').read_text()
for x in ['display.fillRoundRect(8, 54, 154, 88, 10, risk.panel);','drawMetricCard(7, 258, 156, 29);']:
    assert x in td
for x in ['gfx->fillRoundRect(10, 65, 128, 128, 12, risk.panel);','drawRoundedRectCard(143, 164, 87, 29);','drawRoundedRectCard(10, 201, 62, 68);','drawRoundedRectCard(76, 201, 62, 68);','drawRoundedRectCard(143, 201, 87, 68);']:
    assert x in wv
assert 'String directionLongText(float deg)' in wv
for board_name in ['T-Display-S3','Waveshare-ESP32-S3-Touch-LCD-2.8']:
    board=OUT_ROOT/board_name
    if board_name == 'T-Display-S3':
        assert 'lovyan03/LovyanGFX@1.2.7' in (board/'platformio.ini').read_text()
    else:
        assert 'moononournation/GFX Library for Arduino@1.6.0' in (board/'platformio.ini').read_text()
    assert 'ICON_THERMOMETER' in (board/'include/ui_assets.h').read_text()

print('Refactor generated and static checks passed')
