#ifndef SETTINGS_STORE_H
#define SETTINGS_STORE_H

#include <Arduino.h>
#include "app_types.h"

void loadSettings(ControllerSettings& settings);
void saveSettings(const ControllerSettings& settings);
String htmlEscape(const String& input);

#endif
