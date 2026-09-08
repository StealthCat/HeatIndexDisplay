#include <WiFi.h>
#include <math.h>
#include "app_state.h"
#include "ui_state.h"
#include "config_store.h"
#include "time_utils.h"

static bool floatDifferent(float a, float b, float tolerance = 0.01f) {
  if (isnan(a) && isnan(b)) return false;
  if (isnan(a) != isnan(b)) return true;
  return fabsf(a - b) > tolerance;
}

bool weatherDisplayChanged(const WeatherData &before, const WeatherData &after) {
  if (before.valid != after.valid) return true;
  if (!after.valid) return false;

  if (before.dateUtcMs != after.dateUtcMs) return true;
  if (floatDifferent(before.tempF, after.tempF)) return true;
  if (floatDifferent(before.humidity, after.humidity)) return true;
  if (floatDifferent(before.heatIndexF, after.heatIndexF)) return true;
  if (floatDifferent(before.windChillF, after.windChillF)) return true;
  if (floatDifferent(before.dewPointF, after.dewPointF)) return true;
  if (floatDifferent(before.windMph, after.windMph)) return true;
  if (floatDifferent(before.gustMph, after.gustMph)) return true;
  if (floatDifferent(before.windDirDeg, after.windDirDeg)) return true;
  if (floatDifferent(before.yesterdayTempF, after.yesterdayTempF)) return true;
  if (floatDifferent(before.fromYesterdayF, after.fromYesterdayF)) return true;
  if (floatDifferent(before.todayHighF, after.todayHighF)) return true;
  if (floatDifferent(before.todayLowF, after.todayLowF)) return true;
  if (before.summaryValid != after.summaryValid) return true;

  return false;
}

String footerStateKey() {
  String key;
  key.reserve(160);

  key += String((int)WiFi.status());
  key += '|';
  key += setupApStarted ? '1' : '0';
  key += '|';
  key += apiConfigured() ? '1' : '0';
  key += '|';
  key += wx.valid ? '1' : '0';
  key += '|';
  key += dataStale() ? '1' : '0';
  key += '|';
  key += updateClockText();
  key += '|';
  key += lastApiError;

  return key;
}
