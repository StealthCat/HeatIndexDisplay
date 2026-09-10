#include <Arduino.h>
#include <esp_system.h>
#include "app_controller.h"
#include "app_state.h"
#include "display_ui.h"
#include "ui_state.h"

namespace {
constexpr uint8_t BUTTON_BOOT_PIN = 0;
constexpr uint8_t BUTTON_USER_PIN = 14;
constexpr unsigned long BUTTON_DEBOUNCE_MS = 180UL;

bool lastBootButton = HIGH;
bool lastUserButton = HIGH;
unsigned long lastButtonToggleMs = 0;

void setupDisplayButtons() {
  pinMode(BUTTON_BOOT_PIN, INPUT_PULLUP);
  pinMode(BUTTON_USER_PIN, INPUT_PULLUP);
  lastBootButton = digitalRead(BUTTON_BOOT_PIN);
  lastUserButton = digitalRead(BUTTON_USER_PIN);
}

void handleDisplayButtons() {
  const bool bootButton = digitalRead(BUTTON_BOOT_PIN);
  const bool userButton = digitalRead(BUTTON_USER_PIN);
  const bool pressed = (lastBootButton == HIGH && bootButton == LOW) ||
                       (lastUserButton == HIGH && userButton == LOW);
  const unsigned long nowMs = millis();

  if (pressed && nowMs - lastButtonToggleMs >= BUTTON_DEBOUNCE_MS) {
    lastButtonToggleMs = nowMs;
    toggleDisplayPage();
  }

  lastBootButton = bootButton;
  lastUserButton = userButton;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(250);
  Serial.printf("\nHeatIndexDisplay boot: reset_reason=%d free_heap=%u free_psram=%u\n",
                (int)esp_reset_reason(), ESP.getFreeHeap(), ESP.getFreePsram());

  setupDisplayButtons();
  displayBegin();
  drawWaitingScreen();
  appSetup();
  lastFooterStateKey = footerStateKey();
}

void loop() {
  handleDisplayButtons();
  appLoop();
}
