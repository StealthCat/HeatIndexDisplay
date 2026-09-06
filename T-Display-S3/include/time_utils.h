#pragma once
#include <Arduino.h>
#include <time.h>

uint32_t observationAgeSeconds();
bool dataStale();
String formatClockFromEpoch(time_t t);
String formatDateFromEpoch(time_t t);
time_t wxEpochSeconds();
String updateClockText();
String currentDateText();
