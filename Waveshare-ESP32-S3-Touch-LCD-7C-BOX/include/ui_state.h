#pragma once
#include <Arduino.h>
#include "app_state.h"

bool weatherDisplayChanged(const WeatherData &before, const WeatherData &after);
String footerStateKey();
