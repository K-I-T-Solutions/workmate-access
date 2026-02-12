#ifndef ACCESS_API_H
#define ACCESS_API_H

#include "app_types.h"

bool verifyNFCCard(const ControllerSettings& settings, const String& uid);
bool healthCheck(const ControllerSettings& settings, AppState& state, int readyLedPin);

#endif
