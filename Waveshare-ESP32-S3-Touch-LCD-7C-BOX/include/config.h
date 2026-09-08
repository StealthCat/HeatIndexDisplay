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
#define WUNDERGROUND_RECENT_1DAY_URL "https://api.weather.com/v2/pws/observations/all/1day"
#define WUNDERGROUND_RECENT_7DAY_HOURLY_URL "https://api.weather.com/v2/pws/observations/hourly/7day"
#define WUNDERGROUND_HISTORY_URL  "https://api.weather.com/v2/pws/history/all"
#define WUNDERGROUND_DAILY_HISTORY_URL "https://api.weather.com/v2/pws/history/daily"
#define OPEN_METEO_FORECAST_URL    "https://api.open-meteo.com/v1/forecast"
#define FORECAST_REFRESH_SECONDS  900UL
#define FORECAST_RETRY_SECONDS    60UL
#define FORECAST_CARD_SWITCH_SECONDS 30UL
