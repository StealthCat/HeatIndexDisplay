#pragma once

/*
 * Optional compile-time FIRST-BOOT defaults.
 *
 * These values seed Preferences/NVS only when the namespace has never been
 * initialized. Settings saved later from /config persist and override these
 * compiled defaults on subsequent boots. Factory Reset clears NVS, allowing
 * these defaults to seed again on the next boot.
 *
 * Leave strings blank to omit a compiled default. Set numeric values to 0 to
 * use the normal defaults from config.h.
 *
 * Do not commit real passwords/API keys to a public repository.
 */

#define COMPILED_WIFI_SSID                 ""
#define COMPILED_WIFI_PASSWORD             ""
#define COMPILED_AMBIENT_APPLICATION_KEY   ""
#define COMPILED_AMBIENT_API_KEY           ""
#define COMPILED_AMBIENT_STATION_MAC       ""
#define COMPILED_HOSTNAME                  ""
#define COMPILED_TIMEZONE_TZ               ""
#define COMPILED_POLL_SECONDS              0
#define COMPILED_STALE_SECONDS             0
