#include <time.h>
#include "app_state.h"
#include "time_utils.h"

uint32_t observationAgeSeconds() {
  if (!wx.valid) return 0;
  time_t now = time(nullptr);
  if (wx.dateUtcMs > 0 && now > 1700000000) {
    uint64_t nowMs = (uint64_t)now * 1000ULL;
    if (nowMs >= wx.dateUtcMs) {
      uint64_t sec = (nowMs - wx.dateUtcMs) / 1000ULL;
      if (sec > 0xFFFFFFFFULL) return 0xFFFFFFFFUL;
      return (uint32_t)sec;
    }
  }
  return (millis() - wx.fetchedMs) / 1000UL;
}

bool dataStale() {
  // STALE reflects failure to receive a successful API update, not the
  // provider station's observation timestamp. Some PWS/cloud feeds
  // legitimately publish observations several minutes behind real time.
  if (!wx.valid || wx.fetchedMs == 0) return false;
  return ((millis() - wx.fetchedMs) / 1000UL) > cfg.staleSeconds;
}

String formatClockFromEpoch(time_t t) {
  if (t <= 100000) return "--:--";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  int hour = timeinfo.tm_hour % 12;
  if (hour == 0) hour = 12;
  char buf[16];
  snprintf(buf, sizeof(buf), "%d:%02d %s", hour, timeinfo.tm_min,
           timeinfo.tm_hour < 12 ? "AM" : "PM");
  return String(buf);
}

String formatDateFromEpoch(time_t t) {
  if (t <= 100000) return "";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  static const char *WEEKDAYS[] = {
    "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"
  };
  static const char *MONTHS[] = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
  };
  const int weekday = (timeinfo.tm_wday >= 0 && timeinfo.tm_wday < 7)
    ? timeinfo.tm_wday : 0;
  const int month = (timeinfo.tm_mon >= 0 && timeinfo.tm_mon < 12)
    ? timeinfo.tm_mon : 0;
  char buf[32];
  snprintf(buf, sizeof(buf), "%s, %s %d, %d", WEEKDAYS[weekday],
           MONTHS[month], timeinfo.tm_mday, timeinfo.tm_year + 1900);
  return String(buf);
}

time_t wxEpochSeconds() {
  if (wx.dateUtcMs > 0) return (time_t)(wx.dateUtcMs / 1000ULL);
  return time(nullptr);
}

String updateClockText() {
  return formatClockFromEpoch(wxEpochSeconds());
}

String currentDateText() {
  time_t now = time(nullptr);
  if (now <= 100000) now = wxEpochSeconds();
  return formatDateFromEpoch(now);
}
