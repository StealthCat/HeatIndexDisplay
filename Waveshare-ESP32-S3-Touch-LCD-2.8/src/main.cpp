#include <Arduino.h>
#include <esp_system.h>
#include "app_controller.h"
#include "app_state.h"
#include "display_ui.h"
#include "ui_state.h"

void setup() {
  Serial.begin(115200);
  delay(250);
  Serial.printf("\nHeatIndexDisplay boot: reset_reason=%d free_heap=%u free_psram=%u\n",
                (int)esp_reset_reason(), ESP.getFreeHeap(), ESP.getFreePsram());

  displayBegin();
  drawWaitingScreen();
  appSetup();
  lastFooterStateKey = footerStateKey();
}

void loop() {
  appLoop();
}
