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
  char buf[16];
  strftime(buf, sizeof(buf), "%-I:%M %p", &timeinfo);
  return String(buf);
}

String formatDateFromEpoch(time_t t) {
  if (t <= 100000) return "";
  struct tm timeinfo;
  localtime_r(&t, &timeinfo);
  char buf[32];
  strftime(buf, sizeof(buf), "%a, %b %-d, %Y", &timeinfo);
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
