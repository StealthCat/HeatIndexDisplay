#include "weather_source.h"
#include "ambient_weather.h"
#include "wunderground_weather.h"
#include "config_store.h"

bool pollWeatherSource(bool forceRedraw) {
  if (usingWeatherUnderground()) {
    return pollWeatherUnderground(forceRedraw);
  }
  return pollAmbient(forceRedraw);
}
