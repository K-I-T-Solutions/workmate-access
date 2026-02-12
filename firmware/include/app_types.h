#ifndef APP_TYPES_H
#define APP_TYPES_H

#include <Arduino.h>

struct ControllerSettings {
  String wifiSsid;
  String wifiPassword;
  String apiUrl;
  String healthUrl;
  String deviceId;
  String roomId;
};

struct AppState {
  bool lastHealthStatus = false;
  String lastSeenIdentifier = "-";
  String lastAccessResult = "-";
  bool apModeActive = false;
  bool pendingWiFiApply = false;
  unsigned long lastHealthCheck = 0;
  unsigned long lastWiFiReconnectAttempt = 0;
};

#endif
