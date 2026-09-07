from pathlib import Path
import re

projects = [
    Path('T-Display-S3'),
    Path('Waveshare-ESP32-S3-Touch-LCD-2.8'),
]

helper_block = r'''static String providerYmdFromLocal(const String &localTime) {
  if (localTime.length() < 10) return "";
  String ymd;
  ymd.reserve(8);
  for (size_t i = 0; i < 10; i++) {
    char c = localTime[i];
    if (c >= '0' && c <= '9') ymd += c;
  }
  return ymd.length() == 8 ? ymd : String();
}

static int providerSecondsOfDay(const String &localTime) {
  if (localTime.length() < 16) return -1;
  int separator = localTime.indexOf(' ');
  if (separator < 0) separator = localTime.indexOf('T');
  if (separator < 0 || separator + 5 >= (int)localTime.length()) return -1;

  int hour = localTime.substring(separator + 1, separator + 3).toInt();
  int minute = localTime.substring(separator + 4, separator + 6).toInt();
  int second = 0;
  if (separator + 8 < (int)localTime.length() && localTime[separator + 6] == ':') {
    second = localTime.substring(separator + 7, separator + 9).toInt();
  }
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) return -1;
  return hour * 3600 + minute * 60 + second;
}

static bool providerLeapYear(int year) {
  return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
}

static int providerDaysInMonth(int year, int month) {
  static const uint8_t days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
  if (month < 1 || month > 12) return 0;
  if (month == 2 && providerLeapYear(year)) return 29;
  return days[month - 1];
}

static String providerPreviousYmd(const String &ymd) {
  if (ymd.length() != 8) return "";
  int year = ymd.substring(0, 4).toInt();
  int month = ymd.substring(4, 6).toInt();
  int day = ymd.substring(6, 8).toInt();
  if (year < 1970 || month < 1 || month > 12 || day < 1 || day > providerDaysInMonth(year, month)) return "";
  day--;
  if (day < 1) {
    month--;
    if (month < 1) {
      month = 12;
      year--;
    }
    day = providerDaysInMonth(year, month);
  }
  char buf[9];
  snprintf(buf, sizeof(buf), "%04d%02d%02d", year, month, day);
  return String(buf);
}

static bool providerLocalMatchesYmd(const String &localTime, const String &ymd) {
  return providerYmdFromLocal(localTime) == ymd;
}

'''

recent_helpers = r'''static bool fetchRecentWunderground(const char *baseUrl,
                                     DynamicJsonDocument &doc,
                                     String &errorOut,
                                     const char *label) {
  errorOut = "";
  if (WiFi.status() != WL_CONNECTED) {
    errorOut = "Wi-Fi is not connected";
    return false;
  }
  if (!weatherUndergroundConfigured()) {
    errorOut = "Weather Underground API key/station ID are not configured";
    return false;
  }

  String url = String(baseUrl);
  url += "?stationId=";
  url += wuUrlEncode(cfg.wuStationId);
  url += "&format=json&units=e&numericPrecision=decimal&apiKey=";
  url += wuUrlEncode(cfg.wuApiKey);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(12);

  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(15000);
  http.setUserAgent("WS5000-ApparentTemp-ESP32/7.8.1");

  respectWundergroundRateLimit();

  if (!http.begin(client, url)) {
    errorOut = String("Unable to initialize Weather Underground ") + label + " request";
    return false;
  }

  int code = http.GET();
  lastWundergroundRequestMs = millis();
  lastSummaryHttpCode = code;

  if (code != HTTP_CODE_OK) {
    String body = http.getString();
    body.trim();
    if (body.length() > 160) body = body.substring(0, 160);
    errorOut = String("Weather Underground ") + label + " HTTP " + String(code);
    if (body.length()) {
      errorOut += ": ";
      errorOut += body;
    }
    http.end();
    return false;
  }

  StaticJsonDocument<320> filter;
  filter["observations"][0]["obsTimeLocal"] = true;
  filter["observations"][0]["epoch"] = true;
  filter["observations"][0]["imperial"]["tempHigh"] = true;
  filter["observations"][0]["imperial"]["tempLow"] = true;
  filter["observations"][0]["imperial"]["tempAvg"] = true;
  filter["observations"][0]["imperial"]["windgustHigh"] = true;

  DeserializationError jsonErr = deserializeJson(doc, http.getStream(), DeserializationOption::Filter(filter));
  http.end();

  if (jsonErr) {
    errorOut = String("Weather Underground ") + label + " JSON error: " + String(jsonErr.c_str());
    return false;
  }

  JsonArray observations = doc["observations"].as<JsonArray>();
  if (observations.isNull() || observations.size() == 0) {
    errorOut = String("Weather Underground ") + label + " returned no observations";
    return false;
  }
  return true;
}

static bool summarizeRecentWundergroundDay(JsonArray observations,
                                            const String &ymd,
                                            float &high,
                                            float &low,
                                            float &maxGust) {
  bool sawProviderDay = false;
  for (JsonObject point : observations) {
    String localTime = String((const char*)(point["obsTimeLocal"] | ""));
    if (!providerLocalMatchesYmd(localTime, ymd)) continue;

    JsonObject imperial = point["imperial"].as<JsonObject>();
    float pointHigh = wuFloat(imperial["tempHigh"]);
    float pointLow = wuFloat(imperial["tempLow"]);
    float pointAvg = wuFloat(imperial["tempAvg"]);
    float pointGust = wuFloat(imperial["windgustHigh"]);

    if (!isfinite(pointHigh) && isfinite(pointAvg)) pointHigh = pointAvg;
    if (!isfinite(pointLow) && isfinite(pointAvg)) pointLow = pointAvg;

    if (isfinite(pointHigh)) {
      if (!isfinite(high) || pointHigh > high) high = pointHigh;
      sawProviderDay = true;
    }
    if (isfinite(pointLow)) {
      if (!isfinite(low) || pointLow < low) low = pointLow;
      sawProviderDay = true;
    }
    if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) maxGust = pointGust;
  }
  return sawProviderDay && isfinite(high) && isfinite(low);
}

static float nearestRecentWundergroundTemperature(JsonArray observations,
                                                   const String &ymd,
                                                   int targetSeconds) {
  float yesterday = NAN;
  uint32_t bestDifference = UINT32_MAX;

  for (JsonObject point : observations) {
    String localTime = String((const char*)(point["obsTimeLocal"] | ""));
    if (!providerLocalMatchesYmd(localTime, ymd)) continue;

    int pointSeconds = providerSecondsOfDay(localTime);
    if (pointSeconds < 0) continue;

    JsonObject imperial = point["imperial"].as<JsonObject>();
    float pointTemp = wuFloat(imperial["tempAvg"]);
    if (!isfinite(pointTemp)) {
      float pointHigh = wuFloat(imperial["tempHigh"]);
      float pointLow = wuFloat(imperial["tempLow"]);
      if (isfinite(pointHigh) && isfinite(pointLow)) pointTemp = (pointHigh + pointLow) * 0.5f;
      else if (isfinite(pointHigh)) pointTemp = pointHigh;
      else if (isfinite(pointLow)) pointTemp = pointLow;
    }
    if (!isfinite(pointTemp)) continue;

    uint32_t delta = pointSeconds > targetSeconds
                   ? (uint32_t)(pointSeconds - targetSeconds)
                   : (uint32_t)(targetSeconds - pointSeconds);
    if (delta < bestDifference) {
      bestDifference = delta;
      yesterday = pointTemp;
    }
  }
  return yesterday;
}

'''

summary_function = r'''bool fetchWeatherUndergroundSummary(String &errorOut) {
  errorOut = "";
  if (!wx.valid || wx.dateUtcMs == 0) {
    errorOut = "Current observation is not available";
    return false;
  }

  String todayYmd = providerYmdFromLocal(lastWundergroundObsTimeLocal);
  int targetSeconds = providerSecondsOfDay(lastWundergroundObsTimeLocal);

  if (!todayYmd.length()) todayYmd = localDateYmd(wx.dateUtcMs);
  if (targetSeconds < 0) {
    time_t currentSec = (time_t)(wx.dateUtcMs / 1000ULL);
    struct tm localTm;
    localtime_r(&currentSec, &localTm);
    targetSeconds = localTm.tm_hour * 3600 + localTm.tm_min * 60 + localTm.tm_sec;
  }

  String yesterdayYmd = providerPreviousYmd(todayYmd);
  if (!todayYmd.length() || !yesterdayYmd.length() || targetSeconds < 0) {
    errorOut = "Unable to determine Weather Underground provider-local summary time";
    return false;
  }

  float high = wx.tempF;
  float low = wx.tempF;
  float maxGust = isfinite(wx.gustMph) ? wx.gustMph : NAN;
  float yesterday = NAN;
  bool todayOk = false;
  String recentError;

  DynamicJsonDocument recentDoc(49152);
  if (fetchRecentWunderground(WUNDERGROUND_RECENT_7DAY_HOURLY_URL,
                              recentDoc,
                              recentError,
                              "recent 7-day hourly REST")) {
    JsonArray recent = recentDoc["observations"].as<JsonArray>();
    todayOk = summarizeRecentWundergroundDay(recent, todayYmd, high, low, maxGust);
    yesterday = nearestRecentWundergroundTemperature(recent, yesterdayYmd, targetSeconds);
  }

  if (!todayOk) {
    DynamicJsonDocument rapidDoc(49152);
    String rapidError;
    if (fetchRecentWunderground(WUNDERGROUND_RECENT_1DAY_URL,
                                rapidDoc,
                                rapidError,
                                "recent 1-day REST")) {
      todayOk = summarizeRecentWundergroundDay(rapidDoc["observations"].as<JsonArray>(),
                                               todayYmd,
                                               high,
                                               low,
                                               maxGust);
    } else if (!recentError.length()) {
      recentError = rapidError;
    }
  }

  if (!todayOk) {
    DynamicJsonDocument dailyDoc(4096);
    String dailyError;
    bool dailyOk = fetchDailyHistoryDate(todayYmd, dailyDoc, dailyError);
    if (dailyOk) {
      for (JsonObject point : dailyDoc["observations"].as<JsonArray>()) {
        JsonObject imperial = point["imperial"].as<JsonObject>();
        float pointHigh = wuFloat(imperial["tempHigh"]);
        float pointLow = wuFloat(imperial["tempLow"]);
        float pointGust = wuFloat(imperial["windgustHigh"]);
        if (isfinite(pointHigh) && (!isfinite(high) || pointHigh > high)) high = pointHigh;
        if (isfinite(pointLow) && (!isfinite(low) || pointLow < low)) low = pointLow;
        if (isfinite(pointGust) && (!isfinite(maxGust) || pointGust > maxGust)) maxGust = pointGust;
      }
      todayOk = isfinite(high) && isfinite(low);
    }

    if (!todayOk) {
      String fallbackError;
      if (!summarizeWundergroundAllHistory(todayYmd, high, low, maxGust, fallbackError)) {
        errorOut = recentError;
        if (errorOut.length() && dailyError.length()) errorOut += "; daily: ";
        errorOut += dailyError;
        if (errorOut.length() && fallbackError.length()) errorOut += "; archived: ";
        errorOut += fallbackError;
        return false;
      }
      todayOk = true;
    }
  }

  wx.todayHighF = high;
  wx.todayLowF = low;
  wx.maxDailyGustMph = maxGust;
  wx.summaryValid = todayOk && isfinite(wx.todayHighF) && isfinite(wx.todayLowF);
  wx.summaryFetchedMs = millis();

  if (!isfinite(yesterday)) {
    DynamicJsonDocument yesterdayDoc(32768);
    String yesterdayError;
    if (!fetchHistoryDate(yesterdayYmd, yesterdayDoc, yesterdayError)) {
      errorOut = yesterdayError;
      return false;
    }

    yesterday = nearestRecentWundergroundTemperature(yesterdayDoc["observations"].as<JsonArray>(),
                                                     yesterdayYmd,
                                                     targetSeconds);

    if (!isfinite(yesterday)) {
      time_t currentSec = (time_t)(wx.dateUtcMs / 1000ULL);
      struct tm yesterdayTm;
      localtime_r(&currentSec, &yesterdayTm);
      yesterdayTm.tm_mday -= 1;
      yesterdayTm.tm_isdst = -1;
      time_t yesterdaySec = mktime(&yesterdayTm);
      uint64_t targetYesterdayMs = yesterdaySec > 0 ? (uint64_t)yesterdaySec * 1000ULL : 0ULL;
      uint64_t bestDifference = UINT64_MAX;

      for (JsonObject point : yesterdayDoc["observations"].as<JsonArray>()) {
        uint64_t epoch = point["epoch"] | 0ULL;
        JsonObject imperial = point["imperial"].as<JsonObject>();
        float pointTemp = wuFloat(imperial["tempAvg"]);
        if (epoch == 0 || !isfinite(pointTemp)) continue;
        uint64_t pointMs = epoch * 1000ULL;
        uint64_t delta = pointMs > targetYesterdayMs ? pointMs - targetYesterdayMs : targetYesterdayMs - pointMs;
        if (delta < bestDifference) {
          bestDifference = delta;
          yesterday = pointTemp;
        }
      }
    }
  }

  if (!isfinite(yesterday)) {
    errorOut = "Weather Underground REST data did not contain yesterday temperature";
    return false;
  }

  wx.yesterdayTempF = yesterday;
  wx.fromYesterdayF = wx.tempF - yesterday;
  wx.summaryFetchedMs = millis();

  Serial.printf(
    "Weather Underground REST summary: high=%.2fF low=%.2fF yesterday=%.2fF delta=%+.2fF\n",
    wx.todayHighF, wx.todayLowF, wx.yesterdayTempF, wx.fromYesterdayF
  );
  return true;
}'''

for project in projects:
    config = project / 'include/config.h'
    text = config.read_text(encoding='utf-8')
    if 'WUNDERGROUND_RECENT_1DAY_URL' not in text:
        text = text.replace(
            '#define WUNDERGROUND_CURRENT_URL  "https://api.weather.com/v2/pws/observations/current"\n',
            '#define WUNDERGROUND_CURRENT_URL  "https://api.weather.com/v2/pws/observations/current"\n'
            '#define WUNDERGROUND_RECENT_1DAY_URL "https://api.weather.com/v2/pws/observations/all/1day"\n'
            '#define WUNDERGROUND_RECENT_7DAY_HOURLY_URL "https://api.weather.com/v2/pws/observations/hourly/7day"\n'
        )
    config.write_text(text, encoding='utf-8')

    ambient = project / 'src/ambient_weather.cpp'
    text = ambient.read_text(encoding='utf-8')
    old = 'if (!fetchHistory(targetYesterdayMs, 2, yesterdayDoc, yesterdayError)) {'
    new = 'if (!fetchHistory(targetYesterdayMs + 1800000ULL, 24, yesterdayDoc, yesterdayError)) {'
    if old not in text and new not in text:
        raise SystemExit(f'Ambient yesterday lookup pattern missing: {ambient}')
    text = text.replace(old, new)
    text = text.replace('WS5000-ApparentTemp-ESP32/7.8"', 'WS5000-ApparentTemp-ESP32/7.8.1"')
    ambient.write_text(text, encoding='utf-8')

    wu = project / 'src/wunderground_weather.cpp'
    text = wu.read_text(encoding='utf-8')
    text = text.replace('WS5000-ApparentTemp-ESP32/7.8"', 'WS5000-ApparentTemp-ESP32/7.8.1"')

    if 'static String lastWundergroundObsTimeLocal;' not in text:
        text = text.replace(
            'static unsigned long lastWundergroundRequestMs = 0;\n',
            'static unsigned long lastWundergroundRequestMs = 0;\nstatic String lastWundergroundObsTimeLocal;\n'
        )

    if 'static String providerYmdFromLocal' not in text:
        marker = 'static bool fetchHistoryDate('
        pos = text.find(marker)
        if pos < 0:
            raise SystemExit(f'fetchHistoryDate marker missing: {wu}')
        text = text[:pos] + helper_block + text[pos:]

    if 'filter["observations"][0]["obsTimeLocal"] = true;' not in text:
        text = text.replace(
            'filter["observations"][0]["epoch"] = true;\n',
            'filter["observations"][0]["obsTimeLocal"] = true;\nfilter["observations"][0]["epoch"] = true;\n',
            1
        )

    if 'static bool fetchRecentWunderground' not in text:
        marker = 'bool fetchWeatherUndergroundCurrent(String &errorOut) {'
        pos = text.find(marker)
        if pos < 0:
            raise SystemExit(f'current-function marker missing: {wu}')
        text = text[:pos] + recent_helpers + text[pos:]

    if 'lastWundergroundObsTimeLocal = String((const char*)(obs["obsTimeLocal"] | ""));' not in text:
        marker = '  wx.valid = true;\n\n  String foundName'
        replacement = (
            '  wx.valid = true;\n'
            '  lastWundergroundObsTimeLocal = String((const char*)(obs["obsTimeLocal"] | ""));\n'
            '  lastWundergroundObsTimeLocal.trim();\n\n'
            '  String foundName'
        )
        if marker not in text:
            raise SystemExit(f'current observation insertion marker missing: {wu}')
        text = text.replace(marker, replacement, 1)

    pattern = re.compile(
        r'bool fetchWeatherUndergroundSummary\(String &errorOut\) \{.*?\n\}\n\nbool pollWeatherUnderground',
        re.S
    )
    if not pattern.search(text):
        raise SystemExit(f'WU summary function not found: {wu}')
    text = pattern.sub(lambda _m: summary_function + '\n\nbool pollWeatherUnderground', text, count=1)
    wu.write_text(text, encoding='utf-8')

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')
text = text.replace('## Current release: V7.8\n', '## Current release: V7.8.1\n')
text = text.replace(
    'V7.8 keeps the approved production layouts and selectable weather provider, and makes the displayed Today High/Low and From Yesterday values explicitly REST-derived from the configured provider. Ambient uses its device-history REST API; Weather Underground uses its PWS daily/all-history REST APIs with fallback handling.\n',
    'V7.8.1 keeps the approved production layouts and provider selection while making live provider summaries more reliable. Ambient widens its same-time-yesterday REST window. Weather Underground now prefers recent 7-day hourly REST observations for Today High/Low and From Yesterday, then falls back to recent 1-day and archived history products.\n'
)
if '## Production Release V7.8.1' not in text:
    text += '\n\n## Production Release V7.8.1\n\nLive Weather Underground summaries now prefer `/v2/pws/observations/hourly/7day`, use provider-local `obsTimeLocal` for today/yesterday matching, and fall back through `/observations/all/1day` and archived history. Ambient widens the same-time-yesterday REST window. See `RELEASE_V7_8_1_LIVE_PROVIDER_SUMMARY_FIX.md`.\n'
readme.write_text(text, encoding='utf-8')

Path('RELEASE_V7_8_1_LIVE_PROVIDER_SUMMARY_FIX.md').write_text(
    '# Production Release V7.8.1 — Live Provider Summary Fix\n\n'
    'V7.8.1 ports the emulator live-summary fixes back to both production ESP32 targets.\n\n'
    '- Weather Underground uses `/v2/pws/observations/hourly/7day` as the primary live REST source for Today High/Low and the observation nearest the same provider-local time yesterday.\n'
    '- Weather Underground uses `obsTimeLocal` from the provider response rather than assuming the configured/device timezone matches the PWS station timezone.\n'
    '- `/v2/pws/observations/all/1day` is the current-day fallback before archived `/history/daily` and `/history/all` data.\n'
    '- The current observation is included in today\'s extrema so the newest provider sample is represented before it rolls into an hourly/history aggregate.\n'
    '- Ambient Weather retains `/v1/devices/{MAC}` as its provider-history source and widens the same-time-yesterday search window to 30 minutes beyond the target with 24 returned records, selecting the nearest stored observation.\n'
    '- A successful Today High/Low refresh is committed before a separate yesterday lookup can fail, preserving useful provider summary data.\n\n'
    'Both production targets are built with PlatformIO before this release is committed.\n',
    encoding='utf-8'
)

for project in projects:
    wu = (project / 'src/wunderground_weather.cpp').read_text(encoding='utf-8')
    ambient = (project / 'src/ambient_weather.cpp').read_text(encoding='utf-8')
    cfg = (project / 'include/config.h').read_text(encoding='utf-8')
    assert 'WUNDERGROUND_RECENT_7DAY_HOURLY_URL' in cfg
    assert 'WUNDERGROUND_RECENT_1DAY_URL' in cfg
    assert 'providerYmdFromLocal' in wu
    assert 'lastWundergroundObsTimeLocal' in wu
    assert 'recent 7-day hourly REST' in wu
    assert 'recent 1-day REST' in wu
    assert 'obsTimeLocal' in wu
    assert 'targetYesterdayMs + 1800000ULL, 24' in ambient

print('V7.8.1 source migration complete')
