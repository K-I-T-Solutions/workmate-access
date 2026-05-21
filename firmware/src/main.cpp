#include <Arduino.h>
#include <Adafruit_PN532.h>
#include <WiFi.h>
#include <Wire.h>
#include "access_api.h"
#include "app_types.h"
#include "network_manager.h"
#include "settings_store.h"
#include "web_ui.h"

#define PN532_IRQ   (2)
#define PN532_RESET (3)

#define LED_SUCCESS 25
#define LED_DENIED  26
#define LED_READY   27

const unsigned long HEALTH_CHECK_INTERVAL = 30000;
const unsigned long WIFI_RECONNECT_INTERVAL = 5000;

const char* AP_SSID = "AccessController-Setup";
const char* AP_PASSWORD = "12345678";
const char* MDNS_HOSTNAME = "access-controller";

Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);
ControllerSettings settings;
AppState state;

void blinkLED(int pin, int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(200);
    digitalWrite(pin, LOW);
    delay(200);
  }
}

void setupNfc() {
  Serial.println("Initializing PN532 NFC Module...");
  nfc.begin();

  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println("PN532 not found! Check wiring and I2C mode jumpers.");
    while (1);
  }

  Serial.print("Found PN532 chip version: ");
  Serial.println((versiondata >> 24) & 0xFF, HEX);
  nfc.SAMConfig();
  Serial.println("PN532 ready to read NFC cards!");
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n=== S.T.A.R. Labs Access Control ===");

  pinMode(LED_SUCCESS, OUTPUT);
  pinMode(LED_DENIED, OUTPUT);
  pinMode(LED_READY, OUTPUT);
  digitalWrite(LED_READY, HIGH);

  setupNfc();
  loadSettings(settings);

  Serial.println("\nConnecting to WiFi...");
  if (connectWiFi(settings, 15000)) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    state.apModeActive = false;
    if (healthCheck(settings, state, LED_READY)) {
      Serial.println("API connection successful!");
    }
  } else {
    Serial.println("\nWiFi connection failed!");
    startAccessPointMode(state, AP_SSID, AP_PASSWORD);
  }

  setupWebUI(settings, state, MDNS_HOSTNAME, []() {
    state.pendingWiFiApply = true;
  });

  Serial.println("\n=== Ready to scan NFC cards ===");
  Serial.println("Place card or phone near reader...");
}

void loop() {
  if (state.pendingWiFiApply) {
    state.pendingWiFiApply = false;
    applyWiFiSettings(settings, state, AP_SSID, AP_PASSWORD);
  }

  ensureWiFiConnected(settings, state, WIFI_RECONNECT_INTERVAL);
  handleWebUIClient();

  if (millis() - state.lastHealthCheck > HEALTH_CHECK_INTERVAL) {
    healthCheck(settings, state, LED_READY);
    state.lastHealthCheck = millis();
  }

  uint8_t uid[] = {0, 0, 0, 0, 0, 0, 0};
  uint8_t uidLength;
  uint8_t success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 100);
  if (!success) {
    delay(100);
    return;
  }

  Serial.println("\n=== NFC Device Detected ===");
  String uidString;
  uidString.reserve(uidLength * 2);
  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) uidString += "0";
    uidString += String(uid[i], HEX);
  }
  uidString.toUpperCase();

  bool isRandomUID = (uidLength == 4 && uid[0] == 0x08);
  String userIdentifier = isRandomUID ? "PHONE_" + uidString : uidString;
  state.lastSeenIdentifier = userIdentifier;

  if (WiFi.status() == WL_CONNECTED) {
    bool access = false;

    // YubiKey 5 NFC: NDEF-OTP auslesen und per Yubico-API prüfen
    String otp = readYubiKeyOTP(nfc);
    if (otp.length() == 44) {
      Serial.println("YubiKey OTP erkannt: " + otp.substring(0, 12) + "...");
      access = verifyYubiKey(settings, otp);
    } else {
      // Normaler NFC-Chip (UID-basiert)
      access = verifyNFCCard(settings, userIdentifier);
    }

    state.lastAccessResult = access ? "GRANTED" : "DENIED";
    blinkLED(access ? LED_SUCCESS : LED_DENIED, access ? 3 : 2);
  } else {
    Serial.println("! WiFi not connected - offline mode");
    state.lastAccessResult = "OFFLINE";
  }

  Serial.println("==================\n");
  delay(2000);
}
