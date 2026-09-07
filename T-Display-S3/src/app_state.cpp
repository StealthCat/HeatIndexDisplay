#include "app_state.h"

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
unsigned long lastForecastPollMs = 0;
String lastForecastError;
int lastForecastHttpCode = 0;
