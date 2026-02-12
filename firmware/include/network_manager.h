#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include "app_types.h"

bool connectWiFi(const ControllerSettings& settings, unsigned long timeoutMs);
void ensureWiFiConnected(
  const ControllerSettings& settings,
  AppState& state,
  unsigned long reconnectIntervalMs
);
void startAccessPointMode(AppState& state, const char* apSsid, const char* apPassword);
void applyWiFiSettings(
  const ControllerSettings& settings,
  AppState& state,
  const char* apSsid,
  const char* apPassword
);

#endif
