#pragma once

// All user settings are configured from the built-in web UI.

#define DEFAULT_HOSTNAME          "heat-index"
#define DEFAULT_TIMEZONE_TZ       "EST5EDT,M3.2.0,M11.1.0"
#define SETUP_AP_PREFIX           "HeatIndex-Setup"

#define DEFAULT_POLL_SECONDS      60
#define MIN_POLL_SECONDS          15
#define DEFAULT_STALE_SECONDS     180
#define MIN_STALE_SECONDS         30

#define WIFI_CONNECT_TIMEOUT_MS   20000UL
#define WIFI_RETRY_SECONDS        20UL

#define AMBIENT_DEVICES_URL       "https://rt.ambientweather.net/v1/devices"
#define WUNDERGROUND_CURRENT_URL  "https://api.weather.com/v2/pws/observations/current"
#define WUNDERGROUND_HISTORY_URL  "https://api.weather.com/v2/pws/history/all"
