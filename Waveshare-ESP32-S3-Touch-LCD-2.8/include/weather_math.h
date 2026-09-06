#pragma once
#include <Arduino.h>

float dewPointFromTempHumidityF(float tF, float rh);
float nwsHeatIndexF(float t, float rh);
float nwsWindChillF(float t, float windMph);
bool windChillApplies();
float apparentOutdoorF();
const char* apparentTitle();
const char* riskLabel(float hi);
const char* coldRiskLabel(float wc);
const char* apparentRiskLabel();
String directionText(float deg);
