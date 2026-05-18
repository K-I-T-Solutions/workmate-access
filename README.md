# workmate-access

NFC- und OTP-basiertes Zugangskontrollsystem für Räume und Ressourcen mit vollständigem IAM-Dashboard. Ein ESP32-Mikrocontroller liest NFC-Chips und Karten und kommuniziert mit einem FastAPI-Backend, das Berechtigungen prüft, OTP-Codes per SMS oder WhatsApp versendet, YubiKey-OTP validiert, Zigbee-Schlösser steuert und ein vollständiges Audit-Log führt. Das Admin-Dashboard ist per Browser erreichbar, per Keycloak OIDC gesichert und bietet direkte Keycloak-Benutzerverwaltung, Raum-Gruppen, Echtzeit-Benachrichtigungen, Anwesenheits-Tracking, Dark Mode und Gravatar-Profilbilder.

**Live:** https://access.intern.phudevelopement.xyz

## Inhaltsverzeichnis

- [Architektur](#architektur)
- [Hardware](#hardware)
- [Voraussetzungen](#voraussetzungen)
- [Backend-Setup](#backend-setup)
- [Firmware-Setup](#firmware-setup)
- [Umgebungsvariablen](#umgebungsvariablen)
- [Keycloak-Setup](#keycloak-setup)
- [Zigbee-Setup](#zigbee-setup)
- [Datenbankschema](#datenbankschema)
- [API-Referenz](#api-referenz)
- [Zugangslogik](#zugangslogik)
- [Projektstruktur](#projektstruktur)

---

## Architektur

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Netzwerk (LAN/WiFi)                         │
│                                                                      │
│  ┌─────────────┐   HTTP/JSON    ┌──────────────────────────────────┐ │
│  │   ESP32     │ ◄────────────► │   FastAPI-Backend                │ │
│  │  + PN532    │                │   (Python 3.11+)                 │ │
│  │  NFC-Reader │                │                                  │ │
│  └─────────────┘                │  ┌──────────┐  ┌─────────────┐  │ │
│                                 │  │PostgreSQL│  │  Keycloak   │  │ │
│  ┌─────────────┐                │  │    DB    │  │  OIDC/JWKS  │  │ │
│  │  Smartphone │  SMS/WhatsApp  │  └──────────┘  └─────────────┘  │ │
│  │    (OTP)    │ ◄────────────► │                                  │ │
│  └─────────────┘    sent.dm     │  ┌──────────┐  ┌─────────────┐  │ │
│                                 │  │ sent.dm  │  │  YubiCloud  │  │ │
│  ┌─────────────┐                │  │   API    │  │     API     │  │ │
│  │  Admin-     │  HTTPS + OIDC  │  └──────────┘  └─────────────┘  │ │
│  │  Dashboard  │ ◄────────────► │                                  │ │
│  │  (Browser)  │   SSE-Stream   │  ┌──────────────────────────┐   │ │
│  └─────────────┘                │  │  Keycloak Admin API      │   │ │
│                                 │  │  (Service Account)       │   │ │
│  ┌─────────────┐                │  └──────────────────────────┘   │ │
│  │ Zigbee2MQTT │   MQTT (1883)  │                                  │ │
│  │  + Schloss  │ ◄────────────► │  ┌──────────────────────────┐   │ │
│  └─────────────┘                │  │  Event Bus (asyncio)     │   │ │
│                                 │  │  SSE Pub/Sub             │   │ │
│                                 │  └──────────────────────────┘   │ │
│                                 └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

| Komponente | Technologie | Zweck |
|---|---|---|
| ESP32 | C++, PlatformIO, Arduino-Framework | NFC-Lesung, WiFi, eingebetteter Webserver |
| PN532 | I2C, Adafruit PN532-Lib | NFC-Chips und -Karten lesen |
| Backend | FastAPI, SQLAlchemy, Pydantic v2 | REST-API, Zugangsprüfung, OTP, YubiKey |
| Datenbank | PostgreSQL 15+ | Users, Rooms, Room Groups, Chips, YubiKeys, Logs, OTPs, Presence |
| Migrationen | Alembic | Datenbankschema-Versionen |
| OTP-Versand | sent.dm SDK | SMS und WhatsApp-Nachrichten |
| YubiKey | YubiCloud API | Hardware-Token-Validierung |
| Auth | Keycloak 26+ (OIDC, PKCE) | SSO, Admin-Dashboard-Authentifizierung |
| Keycloak Admin | Keycloak Admin REST API | Benutzer/Sessions/Rollen direkt aus Dashboard verwalten |
| Zigbee-Lock | paho-mqtt → Zigbee2MQTT | Türöffner-Steuerung per MQTT, automatisches Wiederverriegeln |
| Echtzeit-Alerts | Server-Sent Events (sse-starlette) | Verweigerungs-Benachrichtigungen live im Dashboard |
| Rate-Limiting | slowapi (120 req/min per IP) | Schutz aller API-Endpunkte vor Missbrauch |
| Reverse Proxy | Caddy | HTTPS via Let's Encrypt (Cloudflare DNS-01) |
| Dashboard-UI | Tailwind CSS, Vanilla JS | Statistik-Dashboard, Landing Page, Dark Mode, Gravatar, Raum-Gruppen, SSO-Tab, Anwesenheit |

---

## Hardware

### Komponenten

| Teil | Modell / Bezeichnung |
|---|---|
| Mikrocontroller | ESP32 (DevKit, 38-Pin) |
| NFC-Reader | PN532 NFC/RFID-Modul |
| Verbindung PN532↔ESP32 | I2C (SDA/SCL) |
| Stromversorgung | 5 V USB oder Netzteil |

### GPIO-Pinbelegung (I2C)

| Signal | ESP32-Pin |
|---|---|
| SDA | GPIO 21 |
| SCL | GPIO 22 |
| GND | GND |
| VCC | 3.3 V |

> **Hinweis:** Der PN532 muss auf I2C-Modus gestellt sein (DIP-Schalter: SEL0=0, SEL1=1).

---

## Voraussetzungen

**Backend**
- Python 3.11+
- PostgreSQL 15+
- pip / virtualenv
- Keycloak 26+ (Realm + Clients konfiguriert, siehe [Keycloak-Setup](#keycloak-setup))

**Firmware**
- [PlatformIO CLI](https://platformio.org/install/cli) oder VS Code + PlatformIO Extension
- USB-Kabel zum ESP32

---

## Backend-Setup

```bash
# 1. Repository klonen
git clone https://github.com/commanderphu/workmate-access.git
cd workmate-access

# 2. Virtuelle Umgebung anlegen
python -m venv .venv
source .venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r backend/requirements.txt

# 4. Umgebungsvariablen konfigurieren
cp .env.example .env
# .env mit echten Werten befüllen (siehe Abschnitt Umgebungsvariablen)

# 5. Datenbank migrieren
cd backend
alembic upgrade head

# 6. Backend starten
uvicorn app.main:app --reload --port 8000
```

Die API ist danach unter `http://localhost:8000` erreichbar.
Swagger-UI: `http://localhost:8000/docs`
Admin-Dashboard: `http://localhost:8000`

### Docker

Das Projekt läuft als einzelner Backend-Container und hängt sich in ein externes Docker-Netzwerk (`core_network`) ein, in dem PostgreSQL und Keycloak bereits laufen.

**Voraussetzung:** Das externe Netzwerk muss existieren:

```bash
docker network create core_network
```

**Starten:**

```bash
docker compose up -d --build
```

**Stoppen / Neu starten:**

```bash
docker compose down
docker compose up -d --build   # mit rebuild
docker compose up -d           # ohne rebuild
```

**Logs ansehen:**

```bash
docker logs -f workmate_access_backend
```

**Einzelnen Rebuild erzwingen:**

```bash
docker compose up -d --force-recreate backend
```

#### docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    container_name: workmate_access_backend
    restart: unless-stopped
    env_file: .env                          # alle Secrets aus .env
    environment:
      DATABASE_URL: postgresql://workmate:workmate@central_postgres:5432/workmate_access
    networks:
      - core_network                        # shared mit Postgres + Keycloak

networks:
  core_network:
    external: true                          # wird nicht von compose verwaltet
```

#### Dockerfile (backend/)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Migrationen laufen automatisch beim Start
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

> **Hinweis:** Alembic-Migrationen laufen automatisch beim Container-Start (`alembic upgrade head`). Beim ersten Start wird die Datenbank vollständig initialisiert.

#### Netzwerk-Topologie

```
core_network (Docker Bridge)
├── central_postgres      ← PostgreSQL (externes Projekt)
├── keycloak              ← Keycloak 26+ (externes Projekt)
└── workmate_access_backend
```

Das Backend erreicht Keycloak intern über `KEYCLOAK_INTERNAL_URL=http://keycloak:8080` (JWKS-Fetch), während das Frontend den öffentlichen `KEYCLOAK_URL` für die OIDC-Weiterleitung nutzt.

### Makefile-Befehle (backend/)

| Befehl | Aktion |
|---|---|
| `make run` | Backend mit Reload starten |
| `make migrate` | `alembic upgrade head` |
| `make revision msg="..."` | Neue Alembic-Migration erstellen |
| `make test` | Tests ausführen (pytest) |

---

## Firmware-Setup

```bash
cd firmware

# Secrets-Datei anlegen
cp include/secrets.h.example include/secrets.h
```

`include/secrets.h` befüllen:

```cpp
#define WIFI_SSID     "DeinNetzwerk"
#define WIFI_PASSWORD "DeinPasswort"
#define API_BASE_URL  "http://192.168.178.100:8000/api/v1"
#define ROOM_ID       "raum-01"
```

```bash
# Firmware bauen und flashen
pio run --target upload

# Seriellen Monitor öffnen
pio device monitor --baud 115200
```

Der ESP32 verbindet sich nach dem Start mit dem WLAN und wartet auf NFC-Karten. Wird eine Karte erkannt, sendet er die UID an das Backend (`POST /access/verify-card`). Die integrierte LED signalisiert den Zugangsstatus.

---

## Umgebungsvariablen

Kopiere `.env.example` nach `.env` und passe die Werte an.

```ini
# Datenbank
DATABASE_URL=postgresql://workmate:workmate@localhost:5432/workmate_access
PROJEKT_NAME=Workmate Access
LOG_LEVEL=INFO

# Keycloak (Frontend-Auth, PKCE)
KEYCLOAK_URL=https://login.example.com          # Public-URL (Issuer-Validierung + Frontend)
KEYCLOAK_INTERNAL_URL=http://keycloak:8080      # Docker-interner Hostname für JWKS-Fetch
KEYCLOAK_CLIENT_ID=workmate-access              # Public PKCE-Client
KEYCLOAK_REALM=kit

# Keycloak Admin Service Account (für SSO-Tab im Dashboard)
KEYCLOAK_ADMIN_CLIENT_ID=workmate-admin
KEYCLOAK_ADMIN_CLIENT_SECRET=<client-secret>   # Aus Keycloak Client → Credentials

# CORS
CORS_ORIGINS=["https://access.example.com","http://localhost:8000"]

# Zugangskontrolle
DEFAULT_LOCK_TIMEOUT=5        # Sekunden, die das Schloss offen bleibt
MAX_FAILED_ATTEMPTS=3         # Fehlversuche bis Sperrung
LOCKOUT_DURATION=300          # Sperrdauer in Sekunden

# sent.dm (OTP via SMS / WhatsApp)
SENT_DM_API_KEY=<api-key>
SENT_DM_CUSTOMER_ID=<profile-uuid>
SENT_DM_OTP_TEMPLATE_ID=otp
SENT_DM_SANDBOX=false         # true = kein echter Versand

# OTP Rate-Limiting
OTP_SEND_MAX_PER_HOUR=5
OTP_VERIFY_MAX_ATTEMPTS=10
OTP_VERIFY_WINDOW_MINUTES=15

# Yubico OTP (YubiCloud)
# API-Key beantragen: https://upgrade.yubico.com/getapikey/
YUBICO_CLIENT_ID=
YUBICO_SECRET_KEY=

# Zigbee2MQTT (optional — für Schloss-Steuerung per MQTT)
ZIGBEE2MQTT_HOST=192.168.178.50   # MQTT-Broker-IP (leer = Zigbee deaktiviert)
ZIGBEE2MQTT_PORT=1883
ZIGBEE2MQTT_USER=                 # optional, falls MQTT Auth aktiviert
ZIGBEE2MQTT_PASSWORD=
ZIGBEE_UNLOCK_PAYLOAD={"state":"UNLOCK"}
ZIGBEE_LOCK_PAYLOAD={"state":"LOCK"}
ZIGBEE_RELOCK_DELAY=5             # Sekunden bis automatisches Wiederverriegeln

# Keycloak Webhook (optional)
WEBHOOK_SECRET=                   # Wenn gesetzt: Header X-Webhook-Secret wird geprüft
```

---

## Keycloak-Setup

### 1. Realm & PKCE-Client (Frontend-Auth)

1. Realm `kit` anlegen (oder vorhandenen verwenden)
2. Client `workmate-access` anlegen:
   - **Client type:** Public
   - **Authentication flow:** Standard flow + PKCE (`S256`)
   - **Valid Redirect URIs:** `https://access.example.com/*`
   - **Web Origins:** `https://access.example.com` (kein Trailing-Slash!)

### 2. Admin Service Account (SSO-Tab im Dashboard)

Damit das Dashboard Benutzer, Sessions und Rollen direkt über die Keycloak Admin API verwalten kann, wird ein dedizierter Service-Account-Client benötigt.

**Client anlegen:**

1. Keycloak Admin → Realm `kit` → **Clients** → **Create client**
2. **Client type:** `OpenID Connect`
3. **Client ID:** `workmate-admin`
4. → **Next**
5. **Client authentication:** `ON`
6. **Authentication flow:** nur **Service accounts roles** aktivieren, alles andere aus
7. → **Next** → **Save**

**Client Secret kopieren:**

- Tab **Credentials** → Secret kopieren
- In `.env` eintragen: `KEYCLOAK_ADMIN_CLIENT_SECRET=<secret>`

**Service Account Rollen zuweisen:**

- Tab **Service account roles** → **Assign role**
- Filter auf **Filter by clients** → Client `realm-management` wählen
- Folgende Rollen zuweisen:

| Rolle | Zweck |
|---|---|
| `view-users` | Benutzer auflisten und lesen |
| `manage-users` | Benutzer anlegen, updaten, sperren, löschen |
| `view-realm` | Realm-Rollen und Infos lesen |
| `manage-realm` | Sessions verwalten |

### Bekannte Fallstricke

| Problem | Lösung |
|---|---|
| Keycloak 26+ liefert `/js/keycloak.js` nicht mehr | `keycloak-js` npm-Paket als `/static/keycloak.js` bündeln |
| `keycloak-js` ist ES-Modul | `import('/static/keycloak.js')` statt `<script src>` |
| JWT `aud`-Claim fehlt bei Public Clients | `verify_aud: False` in der Token-Validierung |
| Docker kann externe Keycloak-Domain nicht auflösen | `KEYCLOAK_INTERNAL_URL=http://keycloak:8080` für JWKS-Fetch setzen |
| CORS-Fehler bei Login | Web Origins **ohne** Trailing-Slash eintragen |
| Admin API gibt 403 | Service Account hat nicht alle `realm-management`-Rollen |

---

## Zigbee-Setup

Das Backend kann Türschlösser direkt über [Zigbee2MQTT](https://www.zigbee2mqtt.io/) steuern. Bei einem gewährten NFC-Zugang wird das Schloss des Raums automatisch geöffnet und nach `ZIGBEE_RELOCK_DELAY` Sekunden wieder verriegelt.

### Voraussetzungen

- Zigbee2MQTT läuft im Netzwerk und ist mit dem Schloss gepaired
- Ein MQTT-Broker ist erreichbar (z. B. Mosquitto)
- Die Geräte-ID des Schlosses ist in Zigbee2MQTT bekannt (z. B. `tuya_lock_01`)

### Raum mit Schloss verknüpfen

Beim Anlegen oder Bearbeiten eines Raums das Feld `zigbee_lock_id` mit der Zigbee2MQTT-Geräte-ID befüllen:

```json
{ "id": "serverroom", "name": "Serverraum", "zigbee_lock_id": "tuya_lock_01" }
```

Das Backend publiziert dann bei Zugang auf das Topic `zigbee2mqtt/tuya_lock_01/set`:

```
→ {"state":"UNLOCK"}
→ (nach ZIGBEE_RELOCK_DELAY Sekunden) {"state":"LOCK"}
```

Ist `ZIGBEE2MQTT_HOST` leer oder ist `zigbee_lock_id` für den Raum nicht gesetzt, wird kein MQTT-Befehl gesendet.

---

## Datenbankschema

### users

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | VARCHAR (PK) | z. B. `KIT-0001` |
| keycloak_id | VARCHAR | Keycloak-Benutzer-UUID |
| username | VARCHAR | Login-Name |
| email | VARCHAR | E-Mail-Adresse |
| phone_number | VARCHAR | E.164-Format, z. B. `+4915712345678` |
| display_name | VARCHAR | Anzeigename |
| role | VARCHAR | `admin` oder `user` |
| is_active | BOOLEAN | Konto aktiv |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| updated_at | TIMESTAMP | Letzte Änderung |

### room_groups

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| name | VARCHAR | Gruppenname (z. B. `Admin Räume`) |
| color | VARCHAR | Hex-Farbe für die Anzeige (z. B. `#6366f1`) |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### rooms

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | VARCHAR (PK) | z. B. `serverroom` |
| name | VARCHAR | Anzeigename des Raums |
| description | TEXT | Optionale Beschreibung |
| zigbee_lock_id | VARCHAR | Optionale Zigbee-Lock-Geräte-ID |
| group_id | INTEGER (FK→room_groups) | Zugehörige Gruppe (optional) |
| is_active | BOOLEAN | Raum aktiv |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### access_permissions

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer |
| room_id | VARCHAR (FK→rooms) | Raum |
| access_level | VARCHAR | `read`, `write`, `admin` |
| is_active | BOOLEAN | Berechtigung aktiv |
| valid_from | DATE (nullable) | Gültig ab Datum |
| valid_until | DATE (nullable) | Gültig bis Datum |
| time_from | TIME (nullable) | Erlaubter Tagesbeginn |
| time_until | TIME (nullable) | Erlaubtes Tagesende |
| weekdays | VARCHAR (nullable) | Erlaubte Wochentage, z. B. `0,1,2,3,4` |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### access_logs

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer (nullable bei unbekannter Karte) |
| room_id | VARCHAR | Raum |
| granted | BOOLEAN | Zugang gewährt? |
| reason | VARCHAR | Ablehnungsgrund |
| device_id | VARCHAR | ESP32-Gerät |
| nfc_chip_id | INTEGER (FK→user_chips) | Verwendeter NFC-Chip |
| timestamp | TIMESTAMP | Zeitpunkt des Versuchs |

### user_chips

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer |
| chip_uid | VARCHAR | NFC-Chip-UID (z. B. `74AFF106`) |
| card_uid | VARCHAR | Karten-UID (falls abweichend) |
| label | VARCHAR | Optionale Bezeichnung |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### user_yubikeys

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer |
| public_id | VARCHAR | YubiKey Public-ID (erste 12 Zeichen des OTP) |
| label | VARCHAR | Optionale Bezeichnung |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### guest_tokens

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | VARCHAR (PK) | UUID des Tokens |
| room_id | VARCHAR (FK→rooms) | Raum für den der Link gilt |
| label | VARCHAR (nullable) | Optionale Beschreibung (z. B. "Lieferant") |
| created_by | VARCHAR (nullable) | Keycloak-Username des Admins |
| expires_at | TIMESTAMP | Ablaufzeit |
| is_used | BOOLEAN | Token eingelöst |
| used_at | TIMESTAMP (nullable) | Einlösezeitpunkt |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### presence

Anwesenheits-Tracking per Toggle-Logik: erster NFC-Scan = Betreten, zweiter = Verlassen.

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer |
| room_id | VARCHAR (FK→rooms) | Raum |
| entered_at | TIMESTAMP | Zeitpunkt des Betretens |
| left_at | TIMESTAMP (nullable) | Zeitpunkt des Verlassens (null = noch anwesend) |

### otp_codes

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| phone_number | VARCHAR | Empfänger (E.164) |
| code | VARCHAR(6) | 6-stelliger Code |
| room_id | VARCHAR | Raum, für den der Code gilt |
| channel | VARCHAR | `sms` oder `whatsapp` |
| is_used | BOOLEAN | Code eingelöst |
| expires_at | TIMESTAMP | Ablaufzeit (15 min nach Erstellung) |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| verified_at | TIMESTAMP | Einlösezeitpunkt |

---

## API-Referenz

Base-URL: `/api/v1`

Alle Admin-Endpunkte erfordern einen gültigen Keycloak-Bearer-Token (`Authorization: Bearer <token>`).

### Dashboard / Statistiken

#### `GET /access/stats`
Gibt eine Übersicht über das gesamte System zurück. Wird vom Dashboard beim Login geladen.

**Response:**
```json
{
  "total_users":   12,
  "total_rooms":   5,
  "total_perms":   28,
  "total_chips":   9,
  "access_today":  34,
  "granted_today": 31,
  "denied_today":  3,
  "recent_logs": [
    {
      "id": 142,
      "user_id": "KIT-0001",
      "room_id": "serverroom",
      "granted": true,
      "reason": "Berechtigung: read",
      "device_id": "esp32_entrance_01",
      "timestamp": "2026-05-18T09:14:00"
    }
  ]
}
```

---

### Zugangsprüfung

#### `POST /access/verify`
Prüft Benutzer-/Raumberechtigung direkt.

#### `POST /access/verify-card`
Prüft Zugang per NFC-Karten-UID und Geräte-ID.

**Request:**
```json
{
  "card_uid": "74AFF106",
  "device_id": "esp32_entrance_01",
  "room_id": "serverroom"
}
```

**Response:**
```json
{
  "access": true,
  "message": "Zugang gewährt",
  "user_id": "KIT-0001",
  "user_name": "Joshua Phu",
  "timestamp": "2026-05-14T12:00:00.000000"
}
```

#### `POST /access/yubikey/verify`
Validiert ein Yubico OTP gegen YubiCloud und prüft die Raumberechtigung.

#### `GET /access/logs`
Zugangsprotokoll abrufen. Query-Parameter: `user_id`, `room_id`, `limit`.

#### `GET /access/logs/export`
Protokoll als CSV-Datei herunterladen.

---

### OTP

#### `POST /access/otp/send`
Sendet einen 6-stelligen OTP-Code per WhatsApp (bevorzugt) oder SMS.

#### `POST /access/otp/verify`
Verifiziert den OTP-Code und prüft die Raumberechtigung.

**OTP-Eigenschaften:**
- 6 Stellen, kryptografisch zufällig
- Gültig für 15 Minuten, einmalig verwendbar
- Rate-Limit: max. 5 Sendungen pro Stunde pro Nummer

---

### Benutzer (lokale DB)

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/users/` | Alle Benutzer auflisten |
| `POST` | `/users/` | Neuen Benutzer anlegen |
| `GET` | `/users/{id}` | Einzelnen Benutzer abrufen |
| `PATCH` | `/users/{id}` | Benutzer aktualisieren |
| `DELETE` | `/users/{id}` | Benutzer deaktivieren |
| `GET` | `/users/{id}/chips` | NFC-Chips auflisten |
| `POST` | `/users/{id}/chips` | NFC-Chip hinzufügen |
| `DELETE` | `/users/{id}/chips/{chip_id}` | NFC-Chip entfernen |
| `GET` | `/users/{id}/yubikeys` | YubiKeys auflisten |
| `POST` | `/users/{id}/yubikeys` | YubiKey registrieren |
| `DELETE` | `/users/{id}/yubikeys/{yk_id}` | YubiKey entfernen |

### Raum-Gruppen

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/room-groups/` | Alle Gruppen auflisten |
| `POST` | `/room-groups/` | Neue Gruppe anlegen |
| `PATCH` | `/room-groups/{id}` | Gruppe umbenennen / Farbe ändern |
| `DELETE` | `/room-groups/{id}` | Gruppe löschen |

### Räume

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/rooms/` | Alle Räume auflisten |
| `POST` | `/rooms/` | Neuen Raum anlegen |
| `GET` | `/rooms/{id}` | Einzelnen Raum abrufen |
| `PATCH` | `/rooms/{id}` | Raum aktualisieren (inkl. `group_id`) |
| `DELETE` | `/rooms/{id}` | Raum deaktivieren |

### Berechtigungen

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/permissions/` | Alle Berechtigungen auflisten |
| `POST` | `/permissions/` | Berechtigung erstellen |
| `PATCH` | `/permissions/{id}` | Zeiteinschränkungen nachträglich ändern |
| `DELETE` | `/permissions/{id}` | Berechtigung entfernen |
| `GET` | `/permissions/export` | Alle Berechtigungen als CSV herunterladen |

**CSV-Export** liefert eine Datei `berechtigungen.csv` mit Benutzer-ID, Anzeigename, Raum, Level und allen Zeitfeldern. Der Download-Button ist im Berechtigungs-Tab des Dashboards integriert.

**Zeitbasierte Felder (alle optional):**

```json
{
  "user_id": "KIT-0001",
  "room_id": "serverroom",
  "access_level": "read",
  "valid_from":  "2026-06-01",
  "valid_until": "2026-08-31",
  "time_from":   "08:00:00",
  "time_until":  "18:00:00",
  "weekdays":    "0,1,2,3,4"
}
```

| Feld | Typ | Beschreibung |
|---|---|---|
| `valid_from` | `date` (nullable) | Berechtigung gilt erst ab diesem Datum |
| `valid_until` | `date` (nullable) | Berechtigung läuft an diesem Datum ab |
| `time_from` | `time` (nullable) | Tagesbeginn des erlaubten Fensters |
| `time_until` | `time` (nullable) | Tagesende des erlaubten Fensters |
| `weekdays` | `string` (nullable) | Erlaubte Wochentage, kommasepariert: `0`=Mo … `6`=So — `null` = alle Tage |

Nicht gesetzte Felder bedeuten keine Einschränkung. Der Ablehnungsgrund wird im Audit-Log protokolliert.

### Gast-Zugang

Zeitlich begrenzte Einmal-Links ohne Keycloak-Account. Wird im Audit-Log protokolliert.

| Methode | Endpunkt | Auth | Beschreibung |
|---|---|---|---|
| `POST` | `/access/guest/generate` | Admin | Gast-Link erstellen |
| `POST` | `/access/guest/use/{id}` | — | Link einlösen (einmalig, öffentlich) |
| `GET` | `/access/guest/list` | Admin | Alle Tokens auflisten |
| `DELETE` | `/access/guest/{id}` | Admin | Token widerrufen |

**Request `generate`:**
```json
{ "room_id": "serverroom", "label": "Lieferant 18.05.", "hours": 8 }
```

**Response `use`:**
```json
{ "access": true, "room_id": "serverroom", "message": "Zugang gewährt", "expires_at": "2026-05-18T17:00:00" }
```

---

### Anwesenheit (Presence)

Erfordert gültigen Keycloak-Bearer-Token.

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/presence/current` | Alle aktuell anwesenden Benutzer (kein `left_at`) |
| `GET` | `/presence/history` | Letzte Anwesenheits-Einträge (Query: `limit`, default 50) |

**Response `/presence/current`:**
```json
[
  {
    "user_id": "KIT-0001",
    "room_id": "serverroom",
    "entered_at": "2026-05-18T08:45:00",
    "left_at": null,
    "display_name": "Joshua Phu",
    "room_name": "Serverraum"
  }
]
```

Das Dashboard zeigt die aktuelle Anwesenheit als grüne Badges auf dem Statistik-Tab.

---

### Echtzeit-Events (SSE)

#### `GET /events/access`

Server-Sent Events Stream. Liefert Echtzeit-Benachrichtigungen bei abgelehnten Zugängen.

**Auth:** Bearer-Token als Query-Parameter (`?token=...`), da `EventSource` keine Custom-Header unterstützt.

**Event-Format:**
```json
{
  "type": "access_denied",
  "user_id": "KIT-0002",
  "room_id": "serverroom",
  "reason": "Zugang nur erlaubt an: Mo, Di, Mi, Do, Fr",
  "timestamp": "2026-05-18T22:13:00"
}
```

Das Dashboard zeigt einen Toast oben rechts, wenn ein Zugang verweigert wird.

---

### Keycloak Webhook

#### `POST /webhooks/keycloak`

Empfängt Events vom Keycloak Event-Listener und schreibt sie ins Audit-Log.

**Optionaler Schutz:** Header `X-Webhook-Secret` wird gegen `WEBHOOK_SECRET` in `.env` geprüft.

**Unterstützte Event-Typen:**

| Keycloak-Event | Eintrag im Audit-Log |
|---|---|
| `LOGIN` | `granted=true`, Reason: `SSO Login` |
| `LOGIN_ERROR` | `granted=false`, Reason: `SSO Login fehlgeschlagen (<IP>)` |
| `LOGOUT` | `granted=false`, Reason: `SSO Logout` |

Alle Einträge erhalten `room_id="__sso__"` zur Unterscheidung von Raum-Zugängen.

**Keycloak konfigurieren:** Admin → Events → Event Listener → HTTP-Plugin auf `POST /webhooks/keycloak`.

---

### Keycloak Admin API (SSO-Management)

Alle Endpunkte erfordern `role=admin` im Keycloak-Token.

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/admin/kc/users` | Keycloak-Benutzer auflisten (Query: `search`) |
| `POST` | `/admin/kc/users` | Benutzer in Keycloak anlegen |
| `GET` | `/admin/kc/users/{kc_id}` | Einzelnen KC-Benutzer abrufen |
| `PATCH` | `/admin/kc/users/{kc_id}` | KC-Benutzer aktualisieren |
| `POST` | `/admin/kc/users/{kc_id}/disable` | Benutzer in Keycloak sperren |
| `POST` | `/admin/kc/users/{kc_id}/enable` | Benutzer in Keycloak entsperren |
| `POST` | `/admin/kc/users/{kc_id}/reset-password` | Passwort zurücksetzen (optional temporär) |
| `DELETE` | `/admin/kc/users/{kc_id}` | Benutzer aus Keycloak löschen |
| `GET` | `/admin/kc/users/{kc_id}/sessions` | Aktive Sessions eines Benutzers |
| `DELETE` | `/admin/kc/users/{kc_id}/sessions` | Alle Sessions eines Benutzers beenden |
| `GET` | `/admin/kc/roles` | Alle Realm-Rollen auflisten |
| `GET` | `/admin/kc/users/{kc_id}/roles` | Rollen eines Benutzers abrufen |
| `POST` | `/admin/kc/users/{kc_id}/roles` | Rolle zuweisen |
| `DELETE` | `/admin/kc/users/{kc_id}/roles/{role}` | Rolle entfernen |

---

## Zugangslogik

### NFC-Zugang (Primär)

1. ESP32 liest NFC-Chip-UID oder Karten-UID
2. `POST /access/verify-card` mit `card_uid` + `device_id` + `room_id`
3. Backend sucht `user_chips` nach UID → findet Benutzer
4. Prüft `access_permissions` für (user, room) inkl. Zeitfelder
5. **Bei Zugang gewährt:**
   - Öffnet Zigbee-Schloss des Raums (falls `zigbee_lock_id` gesetzt)
   - Verriegelt automatisch nach `ZIGBEE_RELOCK_DELAY` Sekunden
   - Aktualisiert Anwesenheits-Eintrag (Toggle: Betreten ↔ Verlassen)
6. **Bei Zugang verweigert:**
   - Publiziert Denial-Event in den SSE Event-Bus → Dashboard-Toast
7. Schreibt Eintrag in `access_logs`
8. Gibt `access: true/false` zurück

### YubiKey-Zugang

1. Benutzer steckt YubiKey und tippt OTP (44 Zeichen)
2. `POST /access/yubikey/verify` mit OTP + `room_id`
3. Backend extrahiert Public-ID (erste 12 Zeichen) → findet Benutzer
4. Validiert OTP gegen YubiCloud
5. Prüft Raumberechtigung

### Gast-Zugang (Einmal-Link)

1. Admin generiert Link im Dashboard → "Gast-Link" im SSO-Tab
2. Link enthält UUID: `POST /access/guest/use/{uuid}`
3. Backend prüft: existiert, nicht verwendet, nicht abgelaufen
4. Zugang wird geloggt, Token als verwendet markiert
5. Link ist danach ungültig

### OTP-Zugang (Fallback / Gäste)

1. Benutzer gibt Telefonnummer ein
2. `POST /access/otp/send` → Code per SMS/WhatsApp
3. Benutzer gibt Code ein
4. `POST /access/otp/verify` → Code-Validierung + Raumberechtigung

### Zugangshierarchie

- `role=admin` → Zugang zu allen Räumen ohne expliziten `access_permissions`-Eintrag
- `role=user` → Zugang nur mit explizitem `access_permissions`-Eintrag

### Zeitbasierte Prüfung

Bei jedem Zugangversuch werden die Zeitfelder der Berechtigung geprüft:

```
Berechtigung gefunden?
    → valid_from überschritten?   → ablehnen: "Berechtigung gilt erst ab …"
    → valid_until abgelaufen?     → ablehnen: "Berechtigung abgelaufen am …"
    → aktueller Wochentag erlaubt? → ablehnen: "Zugang nur erlaubt an: Mo, Di, …"
    → aktuelle Uhrzeit im Fenster? → ablehnen: "Zugang nur zwischen 08:00 und 18:00 Uhr"
    → Zugang gewährt
```

Alle Ablehnungsgründe landen im Audit-Log.

---

## Projektstruktur

```
workmate-access/
├── .env.example                ← Vorlage für .env
├── docker-compose.yml
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── Makefile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             ← FastAPI-App, slowapi Rate-Limiting, alle Router
│       ├── core/
│       │   ├── auth.py         ← Keycloak JWT-Validierung, JWKS-Cache
│       │   ├── config.py       ← Settings inkl. Zigbee + Webhook
│       │   └── database.py     ← SQLAlchemy Engine & Session
│       ├── models/
│       │   ├── user.py
│       │   ├── room_group.py
│       │   ├── room.py
│       │   ├── access_log.py
│       │   ├── access_permission.py ← inkl. zeitbasierte Felder
│       │   ├── user_chip.py
│       │   ├── user_yubikey.py
│       │   ├── otp_code.py
│       │   ├── guest_token.py  ← UUID-Einmal-Links
│       │   └── presence.py     ← Anwesenheits-Tracking
│       ├── api/routes/
│       │   ├── users.py
│       │   ├── rooms.py
│       │   ├── room_groups.py
│       │   ├── permissions.py  ← inkl. PATCH + CSV-Export
│       │   ├── access.py       ← inkl. Stats-Endpunkt
│       │   ├── nfc_chips.py
│       │   ├── yubikeys.py
│       │   ├── guest.py        ← Gast-Token Generierung + Einlösung
│       │   ├── keycloak_admin.py ← Keycloak Admin API Proxy
│       │   ├── events.py       ← SSE-Stream für Echtzeit-Alerts
│       │   ├── webhooks.py     ← Keycloak Event-Listener Webhook
│       │   └── presence.py     ← Anwesenheits-Endpunkte
│       ├── services/
│       │   ├── access_service.py  ← Zeitprüfung, Zigbee-Unlock, Presence-Toggle
│       │   ├── otp_service.py
│       │   ├── yubikey_service.py
│       │   ├── keycloak_admin.py  ← Admin API Client (client_credentials)
│       │   ├── zigbee_service.py  ← MQTT-Steuerung via paho-mqtt
│       │   └── event_bus.py       ← asyncio.Queue-basierter SSE Pub/Sub
│       ├── static/
│       │   ├── index.html      ← Dashboard + Landing Page (Tailwind, PKCE, SSE)
│       │   └── keycloak.js     ← keycloak-js@26.2.4 (gebündelt)
│       └── migrations/
│           └── versions/       ← Alembic-Migrationen
│
└── firmware/
    ├── platformio.ini
    ├── include/
    │   ├── secrets.h.example
    │   └── secrets.h           ← Lokale WiFi-/API-Credentials (nicht committen)
    └── src/
        └── main.cpp            ← ESP32-Hauptprogramm
```

---

## Lizenz

Internes Projekt — PhuDevelopement. Alle Rechte vorbehalten.
