#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include "access_api.h"

namespace {

bool jsonBoolFieldTrue(const String& json, const char* key) {
  String pattern = "\"";
  pattern += key;
  pattern += "\"";

  int keyPos = json.indexOf(pattern);
  if (keyPos < 0) {
    return false;
  }

  int colonPos = json.indexOf(':', keyPos + pattern.length());
  if (colonPos < 0) {
    return false;
  }

  int valuePos = colonPos + 1;
  while (valuePos < json.length() && isspace(static_cast<unsigned char>(json[valuePos]))) {
    valuePos++;
  }

  return json.startsWith("true", valuePos);
}

bool jsonStringField(const String& json, const char* key, String& outValue) {
  String pattern = "\"";
  pattern += key;
  pattern += "\":\"";

  int start = json.indexOf(pattern);
  if (start < 0) {
    return false;
  }

  start += pattern.length();
  int end = json.indexOf('"', start);
  if (end < 0) {
    return false;
  }

  outValue = json.substring(start, end);
  return true;
}

}

bool verifyNFCCard(const ControllerSettings& settings, const String& uid) {
  HTTPClient http;
  http.begin(settings.apiUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  String payload;
  payload.reserve(160 + uid.length());
  payload += "{\"card_uid\":\"";
  payload += uid;
  payload += "\",\"device_id\":\"";
  payload += settings.deviceId;
  payload += "\",\"room_id\":\"";
  payload += settings.roomId;
  payload += "\"}";

  Serial.println("Sending to API...");
  Serial.print("Request: ");
  Serial.println(payload);

  int httpCode = http.POST(payload);
  bool accessGranted = false;

  if (httpCode > 0) {
    String response = http.getString();
    Serial.print("API Response (");
    Serial.print(httpCode);
    Serial.print("): ");
    Serial.println(response);

    if (httpCode == 200) {
      accessGranted = jsonBoolFieldTrue(response, "access");

      if (accessGranted) {
        String userName;
        if (jsonStringField(response, "user_name", userName)) {
          Serial.print("✓ ACCESS GRANTED - Welcome ");
          Serial.print(userName);
          Serial.println("!");
        }

        String userId;
        if (jsonStringField(response, "user_id", userId)) {
          Serial.print("User ID: ");
          Serial.println(userId);
        }
      } else {
        String message;
        if (jsonStringField(response, "message", message)) {
          Serial.print("✗ ACCESS DENIED - ");
          Serial.println(message);
        }
      }
    } else {
      Serial.print("HTTP Error Code: ");
      Serial.println(httpCode);
    }
  } else {
    Serial.print("Connection Error: ");
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
  return accessGranted;
}

bool healthCheck(const ControllerSettings& settings, AppState& state, int readyLedPin) {
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(readyLedPin, LOW);
    state.lastHealthStatus = false;
    return false;
  }

  HTTPClient http;
  http.begin(settings.healthUrl);
  http.setTimeout(3000);
  int httpCode = http.GET();

  bool healthy = (httpCode == 200);
  state.lastHealthStatus = healthy;
  digitalWrite(readyLedPin, healthy ? HIGH : LOW);

  if (!healthy) {
    Serial.println("Health check failed!");
  }

  http.end();
  return healthy;
}
