#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <Adafruit_PN532.h>
#include "access_api.h"

// ─── Modhex-Zeichensatz des Yubico OTP ───────────────────────────────────────
static bool isModhex(char c) {
  return strchr("cbdefghijklnrtuv", c) != nullptr;
}

// ─── NDEF Type-4-Tag lesen (YubiKey 5 NFC) ───────────────────────────────────
// Gibt das 44-stellige Yubico-OTP zurück oder "", wenn keines gefunden.
String readYubiKeyOTP(Adafruit_PN532& nfc) {
  uint8_t resp[64];
  uint8_t respLen;

  // 1. NDEF-Applikation selektieren (AID D2760000850101)
  uint8_t selApp[] = {0x00,0xA4,0x04,0x00,0x07,0xD2,0x76,0x00,0x00,0x85,0x01,0x01,0x00};
  respLen = sizeof(resp);
  if (!nfc.inDataExchange(selApp, sizeof(selApp), resp, &respLen)) return "";
  if (respLen < 2 || resp[respLen-2] != 0x90 || resp[respLen-1] != 0x00) return "";

  // 2. Capability Container (E103) selektieren
  uint8_t selCC[] = {0x00,0xA4,0x00,0x0C,0x02,0xE1,0x03};
  respLen = sizeof(resp);
  if (!nfc.inDataExchange(selCC, sizeof(selCC), resp, &respLen)) return "";

  // 3. CC lesen (15 Bytes) → NDEF-File-ID steht in Byte 9-10
  uint8_t readCC[] = {0x00,0xB0,0x00,0x00,0x0F};
  respLen = sizeof(resp);
  if (!nfc.inDataExchange(readCC, sizeof(readCC), resp, &respLen)) return "";
  if (respLen < 11) return "";
  uint8_t ndefFid[2] = {resp[9], resp[10]};

  // 4. NDEF-Datei selektieren
  uint8_t selNDEF[] = {0x00,0xA4,0x00,0x0C,0x02,ndefFid[0],ndefFid[1]};
  respLen = sizeof(resp);
  if (!nfc.inDataExchange(selNDEF, sizeof(selNDEF), resp, &respLen)) return "";

  // 5. Länge lesen (2 Bytes ab Offset 0)
  uint8_t rdLen[] = {0x00,0xB0,0x00,0x00,0x02};
  respLen = sizeof(resp);
  if (!nfc.inDataExchange(rdLen, sizeof(rdLen), resp, &respLen)) return "";
  if (respLen < 2) return "";
  uint16_t ndefLen = ((uint16_t)resp[0] << 8) | resp[1];
  if (ndefLen == 0 || ndefLen > 120) return "";

  // 6. NDEF-Daten lesen (ab Offset 2, max. 60 Bytes)
  uint8_t toRead = (uint8_t)min((int)ndefLen, 60);
  uint8_t rdData[] = {0x00,0xB0,0x00,0x02,toRead};
  respLen = sizeof(resp);
  if (!nfc.inDataExchange(rdData, sizeof(rdData), resp, &respLen)) return "";

  // 7. URI-Record parsen: Header-Byte überspringen, 0x04 = "https://"
  //    Payload: [0x04][rest-of-url-after-https://]
  //    YubiKey-URL: my.yubico.com/yk/#<otp44>
  String raw = "";
  for (uint8_t i = 0; i < respLen; i++) {
    if (resp[i] >= 0x20 && resp[i] < 0x7F) raw += (char)resp[i];
  }

  int hashPos = raw.lastIndexOf('#');
  if (hashPos < 0) return "";

  String otp = raw.substring(hashPos + 1);
  otp.trim();
  if (otp.length() != 44) return "";
  for (char c : otp) { if (!isModhex(c)) return ""; }

  return otp;
}

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

bool verifyYubiKey(const ControllerSettings& settings, const String& otp) {
  // Endpoint: POST /api/v1/access/yubikey/verify
  String url = settings.apiUrl;
  int lastSlash = url.lastIndexOf('/');
  url = url.substring(0, lastSlash) + "/yubikey/verify";

  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  String payload = "{\"yubikey_otp\":\"" + otp + "\",\"room_id\":\"" + settings.roomId + "\",\"device_id\":\"" + settings.deviceId + "\"}";
  Serial.println("YubiKey verify → " + url);

  int httpCode = http.POST(payload);
  bool granted = false;

  if (httpCode == 200) {
    String resp = http.getString();
    granted = jsonBoolFieldTrue(resp, "access");
    String name;
    if (granted && jsonStringField(resp, "user_name", name)) {
      Serial.println("✓ YubiKey GRANTED - Welcome " + name + "!");
    } else if (!granted) {
      String msg;
      jsonStringField(resp, "message", msg);
      Serial.println("✗ YubiKey DENIED - " + msg);
    }
  } else {
    Serial.println("YubiKey HTTP error: " + String(httpCode));
  }

  http.end();
  return granted;
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
