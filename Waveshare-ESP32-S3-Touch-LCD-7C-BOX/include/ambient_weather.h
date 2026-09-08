#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

bool fetchAmbientDevices(DynamicJsonDocument &doc, String &errorOut);
bool applySelectedDevice(JsonArray devices, bool allowAutoSelect, String &errorOut);
bool fetchAmbientSummary(String &errorOut);
bool pollAmbient(bool forceRedraw = true);
