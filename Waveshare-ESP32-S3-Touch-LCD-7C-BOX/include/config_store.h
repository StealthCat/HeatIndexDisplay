#pragma once
#include <Arduino.h>

String normalizeMac(String mac);
String normalizeStationId(String stationId);
String normalizeWeatherSource(String source);
void applyCompileTimeDefaults();
void loadConfig();
void saveConfig();
bool ambientConfigured();
bool weatherUndergroundConfigured();
bool apiConfigured();
bool usingAmbientWeather();
bool usingWeatherUnderground();
String weatherSourceLabel();
