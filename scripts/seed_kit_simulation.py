#!/usr/bin/env python3
"""
seed_kit_simulation.py — K.I.T. Solutions Simulations-Daten

Importiert Räume, Benutzer, NFC-Chips und Berechtigungen in workmate-access
sowie Abteilungen und Mitarbeiter in workmate-os.

Verwendung:
    python scripts/seed_kit_simulation.py [--dry-run] [--skip-access] [--skip-os]

Konfiguration via Umgebungsvariablen:
    ACCESS_URL          workmate-access API  (default: http://localhost:8000)
    OS_URL              workmate-os API      (default: http://localhost:8001)
    KEYCLOAK_URL        (default: aus .env)
    KEYCLOAK_REALM      (default: kit)
    KC_CLIENT_ID        Service-Account-Client für workmate-access (default: workmate-admin)
    KC_CLIENT_SECRET    Service-Account-Secret
    OS_TOKEN            Bearer-Token für workmate-os (optional, falls anderer Client)
"""

import os
import sys
import uuid
import argparse
import httpx
from datetime import date

# ─── ANSI Farben ─────────────────────────────────────────────────────────────
G = "\033[92m"   # grün
Y = "\033[93m"   # gelb
R = "\033[91m"   # rot
B = "\033[94m"   # blau
DIM = "\033[2m"
RST = "\033[0m"

def ok(msg):   print(f"  {G}✓{RST} {msg}")
def skip(msg): print(f"  {Y}→{RST} {DIM}{msg}{RST}")
def err(msg):  print(f"  {R}✗{RST} {msg}", file=sys.stderr)
def head(msg): print(f"\n{B}▶ {msg}{RST}")

# ─── Konfiguration ────────────────────────────────────────────────────────────
ACCESS_URL       = os.getenv("ACCESS_URL",       "http://localhost:8000")
OS_URL           = os.getenv("OS_URL",           "http://localhost:8001")
KEYCLOAK_URL     = os.getenv("KEYCLOAK_URL",     "https://login.intern.phudevelopement.xyz")
KEYCLOAK_REALM   = os.getenv("KEYCLOAK_REALM",   "kit")
KC_CLIENT_ID     = os.getenv("KC_CLIENT_ID",     "workmate-admin")
KC_CLIENT_SECRET = os.getenv("KC_CLIENT_SECRET", "")
OS_TOKEN_ENV     = os.getenv("OS_TOKEN",         "")

# ─── Simulation-Daten ─────────────────────────────────────────────────────────

ROOM_GROUPS = [
    {"name": "Büroräume", "color": "#6366f1"},
    {"name": "Fahrzeuge", "color": "#f59e0b"},
]

# ag_id → {id, name, group, description}
ROOMS = {
    "ag_001": {"id": "buro-haupteingang",    "name": "Büro Hauptzugang",           "description": "Beatusstraße 56 – Haupteingang",     "group": "Büroräume"},
    "ag_002": {"id": "serverraum",           "name": "Serverraum",                 "description": "Zugang nur für technisches Personal", "group": "Büroräume"},
    "ag_003": {"id": "werkstatt-fabian",     "name": "Werkstatt Fabian",           "description": "Fabians Werkstatt",                  "group": "Büroräume"},
    "ag_004": {"id": "content-studio",       "name": "Content Studio",             "description": "Foto / Video / Stream",              "group": "Büroräume"},
    "ag_005": {"id": "fahrzeug-pool",        "name": "Fahrzeug Pool KO-IT-001",    "description": "Toyota Proace City – Poolwagen",      "group": "Fahrzeuge"},
    "ag_006": {"id": "fahrzeug-etienne",     "name": "Fahrzeug Etienne KO-IT-104", "description": "VW Transporter T6.1 – Etienne",      "group": "Fahrzeuge"},
    "ag_007": {"id": "fahrzeug-sascha",      "name": "Fahrzeug Sascha KO-IT-105",  "description": "BYD Seal 6 DM-i – Sascha",          "group": "Fahrzeuge"},
}

USERS = [
    {
        "id": "KIT-0001", "workmate_id": "WM-100",
        "first_name": "Joshua",   "last_name": "Kuhrau",
        "username": "joshua.kuhrau",   "display_name": "Joshua Kuhrau",
        "email": "joshua@kit-it-koblenz.de",  "phone": "+491622654262",
        "role": "admin",  "employment_type": "OWNER",
        "department": "Geschäftsführung",  "hire_date": "2025-05-01",
        "smartcard": "SC-KIT-100",  "status": "ACTIVE",
        "access_groups": ["ag_001", "ag_002", "ag_003", "ag_004", "ag_005"],
    },
    {
        "id": "KIT-0002", "workmate_id": "WM-101",
        "first_name": "Jessica",  "last_name": "Kuhrau",
        "username": "jessica.kuhrau",  "display_name": "Jessica Kuhrau",
        "email": "jessica@kit-it-koblenz.de",  "phone": "+491620000002",
        "role": "admin",  "employment_type": "PARTNER",
        "department": "Operations",  "hire_date": "2025-05-01",
        "smartcard": "SC-KIT-101",  "status": "ACTIVE",
        "access_groups": ["ag_001", "ag_004", "ag_005"],
    },
    {
        "id": "KIT-0003", "workmate_id": "WM-102",
        "first_name": "Lena",     "last_name": "Hoffmann",
        "username": "lena.hoffmann",   "display_name": "Lena Hoffmann",
        "email": "lena@kit-it-koblenz.de",  "phone": "+491620000003",
        "role": "user",  "employment_type": "SHAREHOLDER",
        "department": "Finance",  "hire_date": "2027-01-01",
        "smartcard": "SC-KIT-102",  "status": "ACTIVE",
        "access_groups": ["ag_001", "ag_004", "ag_005"],
    },
    {
        "id": "KIT-0004", "workmate_id": "WM-103",
        "first_name": "Fabian",   "last_name": "Weber",
        "username": "fabian.weber",    "display_name": "Fabian Weber",
        "email": "fabian@kit-it-koblenz.de",  "phone": "+491620000004",
        "role": "admin",  "employment_type": "SHAREHOLDER",
        "department": "Technology",  "hire_date": "2027-01-01",
        "smartcard": "SC-KIT-103",  "status": "ACTIVE",
        "access_groups": ["ag_001", "ag_002", "ag_003", "ag_004", "ag_005"],
    },
    {
        "id": "KIT-0005", "workmate_id": "WM-104",
        "first_name": "Etienne",  "last_name": "Göken",
        "username": "etienne.goeken",  "display_name": "Etienne Göken",
        "email": "etienne@kit-it-koblenz.de",  "phone": "+491620000005",
        "role": "user",  "employment_type": "EMPLOYEE",
        "department": "Facility & Event IT",  "hire_date": "2031-05-12",
        "smartcard": "SC-KIT-104",  "status": "ACTIVE",
        "access_groups": ["ag_001", "ag_004", "ag_005", "ag_006"],
    },
    {
        "id": "KIT-0006", "workmate_id": "WM-105",
        "first_name": "Sascha",   "last_name": "Müller",
        "username": "sascha.mueller",  "display_name": "Sascha Müller",
        "email": "sascha@kit-it-koblenz.de",  "phone": "+491620000006",
        "role": "user",  "employment_type": "EMPLOYEE",
        "department": "Event IT",  "hire_date": "2028-03-01",
        "smartcard": "SC-KIT-105",  "status": "ACTIVE",
        "access_groups": ["ag_001", "ag_004", "ag_005", "ag_007"],
    },
    {
        "id": "KIT-0007", "workmate_id": "WM-106",
        "first_name": "Tobias",   "last_name": "Wenzel",
        "username": "tobias.wenzel",   "display_name": "Tobias Wenzel",
        "email": "tobias@kit-it-koblenz.de",  "phone": "+491620000007",
        "role": "user",  "employment_type": "WERKSTUDENT",
        "department": "IT Außendienst",  "hire_date": "2031-05-19",
        "smartcard": "SC-KIT-106",  "status": "PENDING",
        "access_groups": [],  # PENDING — noch keine aktiven Berechtigungen
    },
    {
        "id": "KIT-0008", "workmate_id": "WM-107",
        "first_name": "Amir",     "last_name": "Hosseini",
        "username": "amir.hosseini",   "display_name": "Amir Hosseini",
        "email": "amir@kit-it-koblenz.de",  "phone": "+491620000008",
        "role": "user",  "employment_type": "FREELANCER",
        "department": "Technology",  "hire_date": "2031-05-19",
        "smartcard": None,  "status": "PENDING",
        "access_groups": [],  # PENDING + kein Smartcard
    },
    {
        "id": "KIT-0009", "workmate_id": "WM-108",
        "first_name": "Gülcan",   "last_name": "Yilmaz",
        "username": "guelcan.yilmaz",  "display_name": "Gülcan Yilmaz",
        "email": "guelcan@kit-it-koblenz.de",  "phone": "+491620000009",
        "role": "user",  "employment_type": "PRAKTIKUM",
        "department": "Marketing",  "hire_date": "2031-05-14",
        "smartcard": "SC-KIT-108",  "status": "PENDING",
        "access_groups": [],  # PENDING
    },
]

EMPLOYMENT_TYPE_MAP = {
    "OWNER":       "fulltime",
    "PARTNER":     "fulltime",
    "SHAREHOLDER": "fulltime",
    "EMPLOYEE":    "fulltime",
    "WERKSTUDENT": "parttime",
    "FREELANCER":  "external",
    "PRAKTIKUM":   "intern",
}

DEPARTMENTS = list({u["department"] for u in USERS})

# ─── Token-Beschaffung ────────────────────────────────────────────────────────

def fetch_access_token() -> str:
    if not KC_CLIENT_SECRET:
        print(f"{R}KC_CLIENT_SECRET nicht gesetzt.{RST}")
        print(f"  Setze: export KC_CLIENT_SECRET=<secret>")
        sys.exit(1)

    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    resp = httpx.post(url, data={
        "grant_type":    "client_credentials",
        "client_id":     KC_CLIENT_ID,
        "client_secret": KC_CLIENT_SECRET,
    }, timeout=10)
    if resp.status_code != 200:
        print(f"{R}Keycloak-Token-Fehler: {resp.status_code} {resp.text}{RST}")
        sys.exit(1)
    token = resp.json()["access_token"]
    ok(f"Keycloak-Token erhalten (Client: {KC_CLIENT_ID})")
    return token

# ─── API-Helfer ───────────────────────────────────────────────────────────────

def api(client: httpx.Client, method: str, path: str, **kwargs):
    resp = client.request(method, path, **kwargs)
    return resp

def post_or_skip(client: httpx.Client, path: str, body: dict, label: str, dry_run: bool) -> bool:
    if dry_run:
        skip(f"[dry-run] POST {path} — {label}")
        return True
    resp = api(client, "POST", path, json=body)
    if resp.status_code in (200, 201):
        ok(label)
        return True
    elif resp.status_code == 409 or "already" in resp.text.lower() or "existiert" in resp.text.lower():
        skip(f"Bereits vorhanden: {label}")
        return False
    else:
        err(f"{label} → {resp.status_code}: {resp.text[:120]}")
        return False

# ─── workmate-access seeden ───────────────────────────────────────────────────

def seed_access(token: str, dry_run: bool):
    base = f"{ACCESS_URL}/api/v1"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(headers=headers, timeout=15) as c:

        # 1. Raum-Gruppen
        head("Raum-Gruppen")
        group_name_to_id: dict[str, int] = {}

        existing = c.get(f"{base}/room-groups/").json() if not dry_run else []
        for g in existing:
            group_name_to_id[g["name"]] = g["id"]

        for rg in ROOM_GROUPS:
            if rg["name"] in group_name_to_id:
                skip(f"Bereits vorhanden: {rg['name']}")
                continue
            resp = api(c, "POST", f"{base}/room-groups/", json=rg)
            if resp.status_code == 201:
                group_name_to_id[rg["name"]] = resp.json()["id"]
                ok(f"Raum-Gruppe: {rg['name']}")
            elif dry_run:
                skip(f"[dry-run] {rg['name']}")
            else:
                err(f"Raum-Gruppe {rg['name']}: {resp.status_code}")

        # 2. Räume
        head("Räume")
        for ag_id, room in ROOMS.items():
            group_id = group_name_to_id.get(room["group"])
            post_or_skip(c, f"{base}/rooms/", {
                "id":          room["id"],
                "name":        room["name"],
                "description": room["description"],
                "group_id":    group_id,
            }, f"Raum: {room['name']}", dry_run)

        # 3. Benutzer
        head("Benutzer")
        for u in USERS:
            # Deterministischer Platzhalter für Keycloak-UUID (ersetzbar)
            kc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"kit.{u['id']}"))
            post_or_skip(c, f"{base}/users/", {
                "id":           u["id"],
                "workmate_id":  u["workmate_id"],
                "keycloak_id":  kc_uuid,
                "username":     u["username"],
                "display_name": u["display_name"],
                "phone_number": u["phone"],
                "role":         u["role"],
            }, f"User: {u['display_name']} ({u['id']} / {u['workmate_id']})", dry_run)

        # 4. NFC-Chips (Smartcards) — nur ACTIVE mit Karte
        head("NFC-Chips (Smartcards)")
        for u in USERS:
            if not u["smartcard"] or u["status"] != "ACTIVE":
                if u["smartcard"] is None:
                    skip(f"Kein Smartcard: {u['display_name']} (Freelancer)")
                elif u["status"] != "ACTIVE":
                    skip(f"PENDING — kein Chip angelegt: {u['display_name']}")
                continue
            post_or_skip(c, f"{base}/users/{u['id']}/chips", {
                "chip_uid": u["smartcard"],
                "label":    f"Smartcard {u['smartcard']}",
            }, f"Chip {u['smartcard']} → {u['display_name']}", dry_run)

        # 5. Berechtigungen — nur ACTIVE-User mit access_groups
        head("Berechtigungen")
        for u in USERS:
            if not u["access_groups"]:
                skip(f"Keine Berechtigungen: {u['display_name']} (status: {u['status']})")
                continue
            for ag_id in u["access_groups"]:
                room = ROOMS[ag_id]
                post_or_skip(c, f"{base}/permissions/", {
                    "user_id":      u["id"],
                    "room_id":      room["id"],
                    "access_level": "read",
                }, f"{u['id']} → {room['name']}", dry_run)

# ─── workmate-os seeden ───────────────────────────────────────────────────────

def seed_os(token: str, dry_run: bool):
    base = f"{OS_URL}/api"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(headers=headers, timeout=15) as c:

        # 1. Abteilungen
        head("Abteilungen (workmate-os)")
        dept_name_to_id: dict[str, str] = {}

        if not dry_run:
            existing = c.get(f"{base}/departments").json()
            # Response kann list oder dict sein
            dept_list = existing if isinstance(existing, list) else existing.get("departments", [])
            for d in dept_list:
                dept_name_to_id[d["name"]] = d["id"]

        for dept_name in DEPARTMENTS:
            if dept_name in dept_name_to_id:
                skip(f"Bereits vorhanden: {dept_name}")
                continue
            resp = api(c, "POST", f"{base}/departments", json={"name": dept_name}) if not dry_run else None
            if dry_run:
                skip(f"[dry-run] Abteilung: {dept_name}")
            elif resp.status_code == 201:
                dept_name_to_id[dept_name] = resp.json()["id"]
                ok(f"Abteilung: {dept_name}")
            else:
                err(f"Abteilung {dept_name}: {resp.status_code} {resp.text[:80]}")

        # 2. Mitarbeiter
        head("Mitarbeiter (workmate-os)")
        for u in USERS:
            dept_id = dept_name_to_id.get(u["department"])
            kc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"kit.{u['id']}"))
            post_or_skip(c, f"{base}/employees", {
                "employee_code":   u["id"],
                "workmate_id":     u["workmate_id"],
                "first_name":      u["first_name"],
                "last_name":       u["last_name"],
                "email":           u["email"],
                "phone":           u["phone"],
                "employment_type": EMPLOYMENT_TYPE_MAP.get(u["employment_type"], "fulltime"),
                "department_id":   dept_id,
                "hire_date":       u["hire_date"],
                "status":          "active" if u["status"] == "ACTIVE" else "inactive",
            }, f"Mitarbeiter: {u['display_name']} ({u['id']} / {u['workmate_id']})", dry_run)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K.I.T. Simulation-Daten seeden")
    parser.add_argument("--dry-run",     action="store_true", help="Nur anzeigen, nicht schreiben")
    parser.add_argument("--skip-access", action="store_true", help="workmate-access überspringen")
    parser.add_argument("--skip-os",     action="store_true", help="workmate-os überspringen")
    args = parser.parse_args()

    print(f"\n{'='*55}")
    print(f"  K.I.T. Solutions — Simulation-Daten Seed")
    if args.dry_run:
        print(f"  {Y}DRY-RUN Modus — keine Änderungen werden geschrieben{RST}")
    print(f"{'='*55}")
    print(f"  workmate-access : {ACCESS_URL}")
    print(f"  workmate-os     : {OS_URL}")

    # Token holen
    print()
    token = fetch_access_token()
    os_token = OS_TOKEN_ENV or token  # gleicher Token wenn selber Keycloak-Realm

    # workmate-access
    if not args.skip_access:
        print(f"\n{'─'*55}")
        print(f"  workmate-access")
        print(f"{'─'*55}")
        try:
            seed_access(token, args.dry_run)
        except Exception as e:
            err(f"workmate-access fehlgeschlagen: {e}")

    # workmate-os
    if not args.skip_os:
        print(f"\n{'─'*55}")
        print(f"  workmate-os")
        print(f"{'─'*55}")
        try:
            seed_os(os_token, args.dry_run)
        except Exception as e:
            err(f"workmate-os fehlgeschlagen: {e}")

    print(f"\n{'='*55}")
    print(f"  {G}Fertig!{RST}")
    if args.dry_run:
        print(f"  Zum echten Import: --dry-run weglassen")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
