#include <Arduino.h>
#include "app_controller.h"
#include "app_state.h"
#include "display_ui.h"
#include "ui_state.h"

void setup() {
  Serial.begin(115200);
  delay(250);

  displayBegin();
  drawWaitingScreen();
  appSetup();
  lastFooterStateKey = footerStateKey();
}

void loop() {
  appLoop();
}
