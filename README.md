# workmate-access

NFC- und OTP-basiertes Zugangskontrollsystem für Räume und Ressourcen mit vollständigem IAM-Dashboard. Ein ESP32-Mikrocontroller liest NFC-Chips und Karten und kommuniziert mit einem FastAPI-Backend, das Berechtigungen prüft, OTP-Codes per SMS oder WhatsApp versendet, YubiKey-OTP validiert und ein vollständiges Audit-Log führt. Das Admin-Dashboard ist per Browser erreichbar, per Keycloak OIDC gesichert und bietet direkte Keycloak-Benutzerverwaltung, Raum-Gruppen, Dark Mode und Gravatar-Profilbilder.

**Live:** https://access.intern.phudevelopement.xyz

## Inhaltsverzeichnis

- [Architektur](#architektur)
- [Hardware](#hardware)
- [Voraussetzungen](#voraussetzungen)
- [Backend-Setup](#backend-setup)
- [Firmware-Setup](#firmware-setup)
- [Umgebungsvariablen](#umgebungsvariablen)
- [Keycloak-Setup](#keycloak-setup)
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
│  │  (Browser)  │                │  ┌──────────────────────────┐   │ │
│  └─────────────┘                │  │  Keycloak Admin API      │   │ │
│                                 │  │  (Service Account)       │   │ │
│                                 │  └──────────────────────────┘   │ │
│                                 └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

| Komponente | Technologie | Zweck |
|---|---|---|
| ESP32 | C++, PlatformIO, Arduino-Framework | NFC-Lesung, WiFi, eingebetteter Webserver |
| PN532 | I2C, Adafruit PN532-Lib | NFC-Chips und -Karten lesen |
| Backend | FastAPI, SQLAlchemy, Pydantic v2 | REST-API, Zugangsprüfung, OTP, YubiKey |
| Datenbank | PostgreSQL 15+ | Users, Rooms, Room Groups, Chips, YubiKeys, Logs, OTPs |
| Migrationen | Alembic | Datenbankschema-Versionen |
| OTP-Versand | sent.dm SDK | SMS und WhatsApp-Nachrichten |
| YubiKey | YubiCloud API | Hardware-Token-Validierung |
| Auth | Keycloak 26+ (OIDC, PKCE) | SSO, Admin-Dashboard-Authentifizierung |
| Keycloak Admin | Keycloak Admin REST API | Benutzer/Sessions/Rollen direkt aus Dashboard verwalten |
| Reverse Proxy | Caddy | HTTPS via Let's Encrypt (Cloudflare DNS-01) |
| Dashboard-UI | Tailwind CSS, Vanilla JS | Landing Page, Dark Mode, Gravatar, Raum-Gruppen, SSO-Tab |

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

```bash
docker compose up -d --build
```

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
| `DELETE` | `/permissions/{id}` | Berechtigung entfernen |

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
| `POST` | `/admin/kc/users/{kc_id}/reset-password` | Passwort zurücksetzen |
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
4. Prüft `access_permissions` für (user, room)
5. Schreibt Eintrag in `access_logs`
6. Gibt `access: true/false` zurück

### YubiKey-Zugang

1. Benutzer steckt YubiKey und tippt OTP (44 Zeichen)
2. `POST /access/yubikey/verify` mit OTP + `room_id`
3. Backend extrahiert Public-ID (erste 12 Zeichen) → findet Benutzer
4. Validiert OTP gegen YubiCloud
5. Prüft Raumberechtigung

### OTP-Zugang (Fallback / Gäste)

1. Benutzer gibt Telefonnummer ein
2. `POST /access/otp/send` → Code per SMS/WhatsApp
3. Benutzer gibt Code ein
4. `POST /access/otp/verify` → Code-Validierung + Raumberechtigung

### Zugangshierarchie

- `role=admin` → Zugang zu allen Räumen ohne expliziten `access_permissions`-Eintrag
- `role=user` → Zugang nur mit explizitem `access_permissions`-Eintrag

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
│       ├── main.py             ← FastAPI-App, Middleware, Router
│       ├── core/
│       │   ├── auth.py         ← Keycloak JWT-Validierung, JWKS-Cache
│       │   ├── config.py       ← Settings (pydantic_settings)
│       │   └── database.py     ← SQLAlchemy Engine & Session
│       ├── models/
│       │   ├── user.py
│       │   ├── room_group.py
│       │   ├── room.py
│       │   ├── access_log.py
│       │   ├── access_permission.py
│       │   ├── user_chip.py
│       │   ├── user_yubikey.py
│       │   └── otp_code.py
│       ├── api/routes/
│       │   ├── users.py
│       │   ├── rooms.py
│       │   ├── room_groups.py
│       │   ├── permissions.py
│       │   ├── access.py
│       │   ├── nfc_chips.py
│       │   ├── yubikeys.py
│       │   └── keycloak_admin.py  ← Keycloak Admin API Proxy (SSO-Tab)
│       ├── services/
│       │   ├── access_service.py
│       │   ├── otp_service.py
│       │   ├── yubikey_service.py
│       │   └── keycloak_admin.py  ← Admin API Client (client_credentials)
│       ├── static/
│       │   ├── index.html      ← Admin-Dashboard + Landing Page (Tailwind, PKCE)
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
