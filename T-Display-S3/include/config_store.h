#pragma once
#include <Arduino.h>

String normalizeMac(String mac);
void applyCompileTimeDefaults();
void loadConfig();
void saveConfig();
bool apiConfigured();
