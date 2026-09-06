#pragma once
#include <Arduino.h>

bool fetchWeatherUndergroundCurrent(String &errorOut);
bool fetchWeatherUndergroundSummary(String &errorOut);
bool pollWeatherUnderground(bool forceRedraw = true);
