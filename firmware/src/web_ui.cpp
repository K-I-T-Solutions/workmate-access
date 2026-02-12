#include <ESPmDNS.h>
#include <WebServer.h>
#include <WiFi.h>
#include "settings_store.h"
#include "web_ui.h"

namespace {

WebServer webServer(80);
ControllerSettings* g_settings = nullptr;
AppState* g_state = nullptr;
std::function<void()> g_onSettingsSaved;
const char* g_mdnsHostname = "access-controller";

void handleRootPage() {
  String html;
  html.reserve(2600);
  html += "<!doctype html><html><head><meta charset=\"utf-8\">";
  html += "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">";
  html += "<title>Controller Status</title><style>";
  html += "body{font-family:Arial,sans-serif;background:#f4f6f8;color:#222;margin:0;padding:20px;}";
  html += ".card{max-width:760px;margin:0 auto;background:#fff;border-radius:12px;padding:20px;";
  html += "box-shadow:0 2px 14px rgba(0,0,0,.08);}h1{margin-top:0;font-size:24px;}";
  html += ".ok{color:#117a00;font-weight:700;}.bad{color:#b00020;font-weight:700;}";
  html += "table{width:100%;border-collapse:collapse;margin-top:12px;}";
  html += "td{padding:8px;border-bottom:1px solid #eceff3;vertical-align:top;}";
  html += "td:first-child{font-weight:700;width:34%;}";
  html += ".actions{margin-top:16px;display:flex;gap:10px;}";
  html += ".btn{display:inline-block;background:#0b63ce;color:#fff;text-decoration:none;padding:10px 14px;border-radius:8px;font-weight:700;}";
  html += "</style></head><body><div class=\"card\">";
  html += "<h1>Access Controller</h1><table>";
  html += "<tr><td>Device ID</td><td>" + htmlEscape(g_settings->deviceId) + "</td></tr>";
  html += "<tr><td>Room ID</td><td>" + htmlEscape(g_settings->roomId) + "</td></tr>";
  html += "<tr><td>WiFi SSID</td><td>" + htmlEscape(g_settings->wifiSsid) + "</td></tr>";
  html += "<tr><td>WiFi Status</td><td>";
  html += (WiFi.status() == WL_CONNECTED) ? "<span class=\"ok\">CONNECTED</span>" : "<span class=\"bad\">DISCONNECTED</span>";
  html += "</td></tr>";
  html += "<tr><td>IP Address</td><td>";
  html += (WiFi.status() == WL_CONNECTED) ? WiFi.localIP().toString() : "-";
  html += "</td></tr>";
  html += "<tr><td>API URL</td><td>" + htmlEscape(g_settings->apiUrl) + "</td></tr>";
  html += "<tr><td>Health URL</td><td>" + htmlEscape(g_settings->healthUrl) + "</td></tr>";
  html += "<tr><td>API Health</td><td>";
  html += g_state->lastHealthStatus ? "<span class=\"ok\">OK</span>" : "<span class=\"bad\">FAILED</span>";
  html += "</td></tr>";
  html += "<tr><td>Last Identifier</td><td>" + htmlEscape(g_state->lastSeenIdentifier) + "</td></tr>";
  html += "<tr><td>Last Access</td><td>" + htmlEscape(g_state->lastAccessResult) + "</td></tr>";
  html += "</table><div class=\"actions\"><a class=\"btn\" href=\"/settings\">Einstellungen</a></div></div></body></html>";

  webServer.send(200, "text/html", html);
}

void handleSettingsPage() {
  String html;
  html.reserve(3300);
  html += "<!doctype html><html><head><meta charset=\"utf-8\">";
  html += "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">";
  html += "<title>Controller Einstellungen</title><style>";
  html += "body{font-family:Arial,sans-serif;background:#f4f6f8;color:#222;margin:0;padding:20px;}";
  html += ".card{max-width:760px;margin:0 auto;background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 14px rgba(0,0,0,.08);}";
  html += "h1{margin-top:0;font-size:24px;}label{display:block;font-weight:700;margin-top:12px;margin-bottom:6px;}";
  html += "input{width:100%;box-sizing:border-box;padding:10px;border:1px solid #ccd3db;border-radius:8px;font-size:14px;}";
  html += ".row{display:grid;grid-template-columns:1fr;gap:12px;}.actions{margin-top:18px;display:flex;gap:10px;flex-wrap:wrap;}";
  html += "button,.btn{display:inline-block;background:#0b63ce;color:#fff;border:0;padding:10px 14px;border-radius:8px;font-weight:700;text-decoration:none;cursor:pointer;}";
  html += ".hint{color:#5b6470;font-size:13px;margin-top:8px;}.ok{background:#e8f6ea;color:#1d6f2b;padding:8px 10px;border-radius:8px;margin-bottom:10px;}";
  html += "</style></head><body><div class=\"card\"><h1>Controller Einstellungen</h1>";
  if (webServer.hasArg("saved")) {
    html += "<div class=\"ok\">Einstellungen gespeichert.</div>";
  }
  html += "<form method=\"POST\" action=\"/settings/save\">";
  html += "<div class=\"row\">";
  html += "<label for=\"wifi_ssid\">WiFi SSID</label><input id=\"wifi_ssid\" name=\"wifi_ssid\" value=\"" + htmlEscape(g_settings->wifiSsid) + "\" required>";
  html += "<label for=\"wifi_password\">WiFi Passwort</label><input type=\"password\" id=\"wifi_password\" name=\"wifi_password\" value=\"" + htmlEscape(g_settings->wifiPassword) + "\">";
  html += "<label for=\"api_url\">API URL</label><input id=\"api_url\" name=\"api_url\" value=\"" + htmlEscape(g_settings->apiUrl) + "\" required>";
  html += "<label for=\"health_url\">Health URL</label><input id=\"health_url\" name=\"health_url\" value=\"" + htmlEscape(g_settings->healthUrl) + "\" required>";
  html += "<label for=\"device_id\">Device ID</label><input id=\"device_id\" name=\"device_id\" value=\"" + htmlEscape(g_settings->deviceId) + "\" required>";
  html += "<label for=\"room_id\">Room ID</label><input id=\"room_id\" name=\"room_id\" value=\"" + htmlEscape(g_settings->roomId) + "\" required>";
  html += "</div><div class=\"actions\"><button type=\"submit\">Speichern</button><a class=\"btn\" href=\"/\">Zur Übersicht</a></div>";
  html += "<div class=\"hint\">WLAN-Aenderungen werden sofort angewendet. Bei Fehlschlag startet wieder der AP-Modus.</div>";
  html += "</form></div></body></html>";

  webServer.send(200, "text/html", html);
}

void handleSettingsSave() {
  if (webServer.hasArg("wifi_ssid")) g_settings->wifiSsid = webServer.arg("wifi_ssid");
  if (webServer.hasArg("wifi_password")) g_settings->wifiPassword = webServer.arg("wifi_password");
  if (webServer.hasArg("api_url")) g_settings->apiUrl = webServer.arg("api_url");
  if (webServer.hasArg("health_url")) g_settings->healthUrl = webServer.arg("health_url");
  if (webServer.hasArg("device_id")) g_settings->deviceId = webServer.arg("device_id");
  if (webServer.hasArg("room_id")) g_settings->roomId = webServer.arg("room_id");

  g_settings->wifiSsid.trim();
  g_settings->apiUrl.trim();
  g_settings->healthUrl.trim();
  g_settings->deviceId.trim();
  g_settings->roomId.trim();

  saveSettings(*g_settings);
  if (g_onSettingsSaved) {
    g_onSettingsSaved();
  }

  webServer.sendHeader("Location", "/settings?saved=1", true);
  webServer.send(303, "text/plain", "Saved");
}

void handleHealth() {
  webServer.send(200, "application/json", "{\"status\":\"ok\"}");
}

}

void setupWebUI(
  ControllerSettings& settings,
  AppState& state,
  const char* mdnsHostname,
  const std::function<void()>& onSettingsSaved
) {
  g_settings = &settings;
  g_state = &state;
  g_mdnsHostname = mdnsHostname;
  g_onSettingsSaved = onSettingsSaved;

  webServer.on("/", HTTP_GET, handleRootPage);
  webServer.on("/settings", HTTP_GET, handleSettingsPage);
  webServer.on("/settings/save", HTTP_POST, handleSettingsSave);
  webServer.on("/health", HTTP_GET, handleHealth);
  webServer.begin();

  if (state.apModeActive) {
    Serial.print("Web status page: http://");
    Serial.print(WiFi.softAPIP());
    Serial.println("/");
  } else if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Web status page: http://");
    Serial.print(WiFi.localIP());
    Serial.println("/");
  } else {
    Serial.println("Web status page started, waiting for network...");
  }

  if (MDNS.begin(g_mdnsHostname)) {
    MDNS.addService("http", "tcp", 80);
    Serial.print("mDNS: http://");
    Serial.print(g_mdnsHostname);
    Serial.println(".local/");
  } else {
    Serial.println("mDNS start failed.");
  }
}

void handleWebUIClient() {
  webServer.handleClient();
}
