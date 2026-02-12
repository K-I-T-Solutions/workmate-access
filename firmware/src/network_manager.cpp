#include <WiFi.h>
#include "network_manager.h"

bool connectWiFi(const ControllerSettings& settings, unsigned long timeoutMs) {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(settings.wifiSsid.c_str(), settings.wifiPassword.c_str());

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) {
    delay(250);
    Serial.print(".");
  }

  return WiFi.status() == WL_CONNECTED;
}

void ensureWiFiConnected(
  const ControllerSettings& settings,
  AppState& state,
  unsigned long reconnectIntervalMs
) {
  if (state.apModeActive || WiFi.status() == WL_CONNECTED) {
    return;
  }

  unsigned long now = millis();
  if (now - state.lastWiFiReconnectAttempt < reconnectIntervalMs) {
    return;
  }
  state.lastWiFiReconnectAttempt = now;

  Serial.println("WiFi disconnected. Reconnecting...");
  WiFi.reconnect();
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(settings.wifiSsid.c_str(), settings.wifiPassword.c_str());
  }
}

void startAccessPointMode(AppState& state, const char* apSsid, const char* apPassword) {
  WiFi.mode(WIFI_AP);
  bool started = WiFi.softAP(apSsid, apPassword);
  if (!started) {
    Serial.println("Failed to start Access Point mode.");
    return;
  }

  state.apModeActive = true;
  Serial.println("Access Point mode active.");
  Serial.print("AP SSID: ");
  Serial.println(apSsid);
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());
}

void applyWiFiSettings(
  const ControllerSettings& settings,
  AppState& state,
  const char* apSsid,
  const char* apPassword
) {
  if (settings.wifiSsid.isEmpty()) {
    Serial.println("WiFi SSID is empty. Keeping current network mode.");
    return;
  }

  WiFi.softAPdisconnect(true);
  state.apModeActive = false;
  WiFi.disconnect(true);
  delay(200);

  Serial.println("Applying WiFi settings...");
  if (connectWiFi(settings, 10000)) {
    Serial.println("WiFi reconnected with updated settings.");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Updated WiFi connect failed.");
    startAccessPointMode(state, apSsid, apPassword);
  }
}
