#pragma once
#include <Arduino.h>

bool fetchForecastHighLow(String &errorOut);
bool pollForecastIfDue(bool forceRedraw);
bool forecastShowsTomorrow();
