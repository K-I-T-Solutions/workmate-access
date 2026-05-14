# workmate-access

Workmate Access ist ein NFC- und OTP-basiertes Zugangskontrollsystem für Räume und Ressourcen. Ein ESP32-Mikrocontroller liest NFC-Chips und kommuniziert mit einem FastAPI-Backend, das Berechtigungen prüft, OTP-Codes per SMS oder WhatsApp versendet und ein Audit-Log führt.

## Inhaltsverzeichnis

- [Architektur](#architektur)
- [Hardware](#hardware)
- [Voraussetzungen](#voraussetzungen)
- [Backend-Setup](#backend-setup)
- [Firmware-Setup](#firmware-setup)
- [Umgebungsvariablen](#umgebungsvariablen)
- [Datenbankschema](#datenbankschema)
- [API-Referenz](#api-referenz)
- [OTP-Flow](#otp-flow)
- [Zugangslogik](#zugangslogik)
- [ESP32 Web-UI](#esp32-web-ui)
- [TODOs](#todos)

---

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                         Netzwerk (LAN/WiFi)                     │
│                                                                  │
│  ┌─────────────┐   HTTP/JSON    ┌─────────────────────────────┐ │
│  │   ESP32     │ ◄────────────► │   FastAPI-Backend           │ │
│  │  + PN532    │                │   (Python 3.11+)            │ │
│  │  NFC-Reader │                │                             │ │
│  └─────────────┘                │  ┌──────────┐ ┌──────────┐ │ │
│                                 │  │PostgreSQL│ │ Alembic  │ │ │
│  ┌─────────────┐                │  │   DB     │ │Migrations│ │ │
│  │  Smartphone │  SMS/WhatsApp  │  └──────────┘ └──────────┘ │ │
│  │    (OTP)    │ ◄────────────► │                             │ │
│  └─────────────┘    sent.dm     │  ┌──────────┐              │ │
│                                 │  │ sent.dm  │              │ │
│  ┌─────────────┐                │  │  API     │              │ │
│  │  Admin-UI   │   HTTP/JSON    │  └──────────┘              │ │
│  │ (Browser)   │ ◄────────────► │                             │ │
│  └─────────────┘                └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

| Komponente | Technologie | Zweck |
|---|---|---|
| ESP32 | C++, PlatformIO, Arduino-Framework | NFC-Lesung, WiFi, eingebetteter Webserver |
| PN532 | I2C, Adafruit PN532-Lib | NFC-Chip und -Karten lesen |
| Backend | FastAPI, SQLAlchemy, Pydantic v2 | REST-API, Zugangsprüfung, OTP |
| Datenbank | PostgreSQL 15+ | Users, Rooms, Access-Logs, OTP-Codes |
| Migrationen | Alembic | Datenbankschema-Versionen |
| OTP-Versand | sent.dm SDK | SMS und WhatsApp-Nachrichten |
| Auth | Keycloak (OIDC) | Admin-Authentifizierung |

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
- (Optional) Keycloak-Instanz für Admin-Auth

**Firmware**
- [PlatformIO CLI](https://platformio.org/install/cli) oder VS Code + PlatformIO Extension
- USB-Kabel zum ESP32

---

## Backend-Setup

```bash
# 1. Repository klonen
git clone <repo-url>
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
# oder:
make run
```

Die API ist danach unter `http://localhost:8000` erreichbar.  
Swagger-UI: `http://localhost:8000/docs`

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

Der ESP32 verbindet sich nach dem Start mit dem WLAN und wartet auf NFC-Karten. Wird eine Karte erkannt, sendet er die UID an das Backend (`POST /access/verify`). Die integrierte LED signalisiert den Zugansstatus.

---

## Umgebungsvariablen

Kopiere `.env.example` nach `.env` und passe die Werte an.

```ini
# Datenbank
DATABASE_URL=postgresql://user:password@host:5432/workmate_access
PROJEKT_NAME=Workmate Access

# Keycloak (Admin-Auth)
KEYCLOAK_URL=https://login.example.com
KEYCLOAK_CLIENT_ID=workmate-backend
KEYCLOAK_CLIENT_SECRET=<secret>
KEYCLOAK_REALM=kit

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Zugangskontrolle
DEFAULT_LOCK_TIMEOUT=5        # Sekunden, die das Schloss offen bleibt
MAX_FAILED_ATTEMPTS=3         # Fehlversuche bis Sperrung
LOCKOUT_DURATION=300          # Sperrdauer in Sekunden

# Logging
LOG_LEVEL=INFO

# sent.dm (OTP via SMS / WhatsApp)
SENT_DM_API_KEY=<api-key>
SENT_DM_CUSTOMER_ID=<profile-id>        # Profil-UUID mit Guthaben
SENT_DM_OTP_TEMPLATE_ID=<template-id>  # Vorab genehmigtes Template
SENT_DM_SANDBOX=false                   # true = kein echter Versand
```

> **Sandbox-Modus:** `SENT_DM_SANDBOX=true` sendet keine echten Nachrichten — nützlich für Tests ohne Guthaben.

---

## Datenbankschema

### users

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | VARCHAR (PK) | z. B. `KIT-0001` |
| keycloak_id | VARCHAR | Keycloak-Benutzer-UUID |
| email | VARCHAR | E-Mail-Adresse |
| phone_number | VARCHAR | E.164-Format, z. B. `+491622654262` |
| display_name | VARCHAR | Anzeigename |
| role | VARCHAR | `admin`, `user`, etc. |
| is_active | BOOLEAN | Konto aktiv |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| updated_at | TIMESTAMP | Letzte Änderung |

### rooms

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | VARCHAR (PK) | z. B. `raum-01` |
| name | VARCHAR | Anzeigename des Raums |
| description | TEXT | Optionale Beschreibung |
| is_active | BOOLEAN | Raum aktiv |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### access_permissions

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer |
| room_id | VARCHAR (FK→rooms) | Raum |
| granted_by | VARCHAR | Admin, der die Berechtigung erteilt hat |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### access_logs

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer (nullable bei unbekannter Karte) |
| room_id | VARCHAR | Raum |
| chip_uid | VARCHAR | UID des NFC-Chips |
| access_granted | BOOLEAN | Zugang gewährt? |
| reason | VARCHAR | Ablehnungsgrund (wenn kein Zugang) |
| timestamp | TIMESTAMP | Zeitpunkt des Versuchs |

### user_chips

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| user_id | VARCHAR (FK→users) | Benutzer |
| chip_uid | VARCHAR | NFC-Chip-UID |
| chip_type | VARCHAR | `nfc` oder `card` |
| label | VARCHAR | Optionale Bezeichnung |
| is_active | BOOLEAN | Chip aktiv |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

### otp_codes

| Spalte | Typ | Beschreibung |
|---|---|---|
| id | INTEGER (PK) | Auto-Increment |
| phone_number | VARCHAR | Empfänger (E.164) |
| code | VARCHAR(6) | 6-stelliger Code |
| room_id | VARCHAR | Raum, für den der Code gilt |
| channel | VARCHAR | `sms` oder `whatsapp` |
| is_used | BOOLEAN | Code eingelöst oder ungültig |
| expires_at | TIMESTAMP | Ablaufzeit (5 min nach Erstellung) |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| verified_at | TIMESTAMP | Einlösezeitpunkt |

---

## API-Referenz

Base-URL: `/api/v1`

### Zugangsprüfung

#### `POST /access/verify`

Prüft, ob ein NFC-Chip Zugang zu einem Raum hat.

**Request:**
```json
{
  "chip_uid": "A1B2C3D4",
  "room_id": "raum-01"
}
```

**Response 200 (Zugang gewährt):**
```json
{
  "access": true,
  "message": "Zugang gewährt",
  "user_id": "KIT-0001",
  "user_name": "Joshua Phu",
  "timestamp": "2026-05-04T12:00:00.000000"
}
```

**Response 200 (Kein Zugang):**
```json
{
  "access": false,
  "message": "Keine Berechtigung für diesen Raum",
  "user_id": null,
  "user_name": null,
  "timestamp": "2026-05-04T12:00:00.000000"
}
```

---

### OTP

#### `POST /access/otp/send`

Generiert einen 6-stelligen OTP-Code und versendet ihn per WhatsApp (bevorzugt) oder SMS.

**Request:**
```json
{
  "phone_number": "+491622654262",
  "room_id": "raum-01"
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "OTP gesendet via SMS",
  "channel": "sms"
}
```

**Response 502** — sent.dm-Versand fehlgeschlagen:
```json
{
  "detail": "Nachricht konnte nicht gesendet werden: ..."
}
```

> Telefonnummer muss im E.164-Format angegeben werden (z. B. `+491622654262`, nicht `+4901622654262`).

---

#### `POST /access/otp/verify`

Verifiziert einen OTP-Code und prüft anschließend die Raumberechtigung des Benutzers.

**Request:**
```json
{
  "phone_number": "+491622654262",
  "code": "527511",
  "room_id": "raum-01"
}
```

**Response 200 (Zugang gewährt):**
```json
{
  "access": true,
  "message": "Zugang gewährt",
  "user_id": "KIT-0001",
  "user_name": "Joshua Phu",
  "timestamp": "2026-05-04T12:00:00.000000"
}
```

**Response 200 (Ungültiger Code):**
```json
{
  "access": false,
  "message": "OTP ungültig oder abgelaufen",
  "user_id": null,
  "user_name": null,
  "timestamp": "2026-05-04T12:00:00.000000"
}
```

**Response 422** — Validierungsfehler (Code nicht 6-stellig, Nummer nicht E.164):
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "code"],
      "msg": "Value error, code muss genau 6 Ziffern haben"
    }
  ]
}
```

---

### Benutzer

#### `GET /users`
Alle Benutzer auflisten.

#### `POST /users`
Neuen Benutzer anlegen.

**Request:**
```json
{
  "id": "KIT-0002",
  "email": "max@example.com",
  "phone_number": "+491511234567",
  "display_name": "Max Mustermann",
  "role": "user"
}
```

#### `GET /users/{user_id}`
Einzelnen Benutzer abrufen.

#### `PUT /users/{user_id}`
Benutzer aktualisieren.

#### `DELETE /users/{user_id}`
Benutzer deaktivieren.

#### `GET /users/{user_id}/chips`
NFC-Chips eines Benutzers auflisten.

#### `POST /users/{user_id}/chips`
NFC-Chip einem Benutzer zuordnen.

**Request:**
```json
{
  "chip_uid": "A1B2C3D4",
  "chip_type": "nfc",
  "label": "Büroschlüssel"
}
```

---

### Räume

#### `GET /rooms`
Alle Räume auflisten.

#### `POST /rooms`
Neuen Raum anlegen.

#### `GET /rooms/{room_id}`
Einzelnen Raum abrufen.

#### `GET /rooms/{room_id}/access-logs`
Zugangsprotokoll eines Raums abrufen.

---

## OTP-Flow

```
Benutzer                  ESP32 / App            Backend              sent.dm
   │                          │                     │                    │
   │   Zugangswunsch          │                     │                    │
   │─────────────────────────►│                     │                    │
   │                          │  POST /otp/send     │                    │
   │                          │────────────────────►│                    │
   │                          │                     │  WhatsApp-Check    │
   │                          │                     │───────────────────►│
   │                          │                     │◄───────────────────│
   │                          │                     │  SMS/WA senden     │
   │                          │                     │───────────────────►│
   │                          │◄────────────────────│                    │
   │   "Code gesendet"        │                     │                    │
   │◄─────────────────────────│                     │                    │
   │                          │                     │                    │
   │   Code eingeben          │                     │                    │
   │─────────────────────────►│                     │                    │
   │                          │  POST /otp/verify   │                    │
   │                          │────────────────────►│                    │
   │                          │                     │  Code + User +     │
   │                          │                     │  Berechtigung      │
   │                          │                     │  prüfen            │
   │                          │◄────────────────────│                    │
   │   Zugang ✓ / ✗           │                     │                    │
   │◄─────────────────────────│                     │                    │
```

**OTP-Eigenschaften:**
- 6 Stellen, kryptografisch zufällig (`secrets.choice`)
- Gültig für 5 Minuten
- Einmalig verwendbar (nach Verifikation sofort als `is_used=true` markiert)
- Kanalwahl: WhatsApp wenn verfügbar (Contacts-API), sonst SMS
- Vorherige offene Codes für dieselbe Nummer werden automatisch invalidiert

---

## Zugangslogik

### NFC-Zugang (Primär)

1. ESP32 liest NFC-Chip-UID
2. `POST /access/verify` mit `chip_uid` + `room_id`
3. Backend sucht `user_chips` nach UID → findet Benutzer
4. Prüft `access_permissions` für (user, room)
5. Schreibt Eintrag in `access_logs`
6. Gibt `access: true/false` zurück

### OTP-Zugang (Fallback / Gäste)

1. Benutzer gibt Telefonnummer ein
2. `POST /access/otp/send` → Code per SMS/WhatsApp
3. Benutzer gibt Code ein
4. `POST /access/otp/verify` → Code-Validierung + Raumberechtigung prüfen
5. Zugang bei `access: true`

### Rate-Limiting / Sperrung

- Nach `MAX_FAILED_ATTEMPTS` (default: 3) Fehlversuchen wird ein Konto für `LOCKOUT_DURATION` Sekunden (default: 300 s = 5 min) gesperrt.
- Admins (`role=admin`) haben Zugang zu allen Räumen, ohne `access_permissions`-Eintrag.

---

## ESP32 Web-UI

Der ESP32 hostet einen eingebetteten Webserver, der über die IP-Adresse im Browser erreichbar ist.

- **WiFi-Konfiguration:** SSID und Passwort können per AP-Modus eingestellt werden
- **Status-Seite:** Zeigt aktuelle IP, WLAN-Signal, letzte NFC-Lesung
- **OTP-Formular:** Telefonnummer eingeben → Code anfordern → Code verifizieren

Die statische `index.html` befindet sich in `backend/app/static/index.html` und wird vom Backend ausgeliefert.

---

## TODOs

### Kritisch

- [ ] Keycloak-Auth vollständig implementieren (JWT-Validierung in FastAPI-Middleware)
- [ ] HTTPS für Backend-Kommunikation (Let's Encrypt oder internes Zertifikat)
- [ ] ESP32-Firmware: TLS-Zertifikat für HTTPS-Requests hinterlegen

### Hoch

- [ ] Rate-Limiting für OTP-Endpunkte (max. X Anfragen pro Nummer pro Stunde)
- [ ] Admin-Dashboard (Web-UI für Benutzer-/Raumverwaltung)
- [ ] MQTT-Integration für Echtzeit-Events (Tür-offen-Status, Alarm)
- [ ] Carrier-Freigabe für SMS-Versand abwarten (sent.dm Sender-Profil-Verifizierung)

### Mittel

- [ ] Push-Benachrichtigungen bei Zugangsverweigerung (z. B. Telegram-Bot)
- [ ] CSV/PDF-Export des Zugangs-Logs
- [ ] Mehrere NFC-Chips pro Benutzer im Frontend verwalten
- [ ] OTP-Fallback per E-Mail (wenn keine Telefonnummer hinterlegt)
- [ ] ESP32: Deep-Sleep-Modus zwischen NFC-Scans für Batteriebetrieb

---

## Projektstruktur

```
workmate-access/
├── .env                        ← Lokale Konfiguration (nicht committen)
├── .env.example                ← Vorlage für .env
├── .venv/                      ← Python-Virtualenv (nicht committen)
├── README.md
│
├── backend/
│   ├── alembic.ini
│   ├── Makefile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             ← FastAPI-App, Middleware, Router
│   │   ├── core/
│   │   │   ├── config.py       ← Settings (pydantic_settings)
│   │   │   └── database.py     ← SQLAlchemy Engine & Session
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── room.py
│   │   │   ├── access_log.py
│   │   │   ├── access_permission.py
│   │   │   ├── user_chip.py
│   │   │   └── otp_code.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── room.py
│   │   │   └── access.py       ← OTP + Verify-Schemas
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── users.py
│   │   │       ├── rooms.py
│   │   │       └── access.py   ← /verify, /otp/send, /otp/verify
│   │   ├── services/
│   │   │   ├── access_service.py
│   │   │   └── otp_service.py
│   │   └── static/
│   │       └── index.html      ← ESP32 Web-UI
│   └── migrations/
│       ├── env.py
│       └── versions/
│           └── *.py            ← Alembic-Migrationen
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
