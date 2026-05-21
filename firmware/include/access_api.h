#ifndef ACCESS_API_H
#define ACCESS_API_H

#include <Adafruit_PN532.h>
#include "app_types.h"

bool verifyNFCCard(const ControllerSettings& settings, const String& uid);
bool verifyYubiKey(const ControllerSettings& settings, const String& otp);
String readYubiKeyOTP(Adafruit_PN532& nfc);
bool healthCheck(const ControllerSettings& settings, AppState& state, int readyLedPin);

#endif
