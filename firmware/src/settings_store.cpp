#include <Preferences.h>
#include "settings_store.h"
#include "secrets.h"

namespace {
Preferences preferences;
}

void loadSettings(ControllerSettings& settings) {
  preferences.begin("controller", true);
  settings.wifiSsid = preferences.getString("wifi_ssid", WIFI_SSID);
  settings.wifiPassword = preferences.getString("wifi_pass", WIFI_PASSWORD);
  settings.apiUrl = preferences.getString("api_url", API_URL);
  settings.healthUrl = preferences.getString("health_url", HEALTH_URL);
  settings.deviceId = preferences.getString("device_id", DEVICE_ID);
  settings.roomId = preferences.getString("room_id", ROOM_ID);
  preferences.end();
}

void saveSettings(const ControllerSettings& settings) {
  preferences.begin("controller", false);
  preferences.putString("wifi_ssid", settings.wifiSsid);
  preferences.putString("wifi_pass", settings.wifiPassword);
  preferences.putString("api_url", settings.apiUrl);
  preferences.putString("health_url", settings.healthUrl);
  preferences.putString("device_id", settings.deviceId);
  preferences.putString("room_id", settings.roomId);
  preferences.end();
}

String htmlEscape(const String& input) {
  String out;
  out.reserve(input.length() + 16);
  for (size_t i = 0; i < input.length(); i++) {
    char c = input[i];
    switch (c) {
      case '&': out += "&amp;"; break;
      case '<': out += "&lt;"; break;
      case '>': out += "&gt;"; break;
      case '"': out += "&quot;"; break;
      case '\'': out += "&#39;"; break;
      default: out += c; break;
    }
  }
  return out;
}
