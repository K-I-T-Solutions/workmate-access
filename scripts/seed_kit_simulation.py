#!/usr/bin/env python3
"""
seed_kit_simulation.py — K.I.T. Solutions Simulations-Daten

Schreibt Räume, Benutzer, NFC-Chips und Berechtigungen direkt in die Datenbank.

Verwendung:
    python scripts/seed_kit_simulation.py [--dry-run]

Konfiguration via Umgebungsvariablen:
    ACCESS_DB   postgresql://workmate:workmate@172.19.0.31:5432/workmate_access
    OS_DB       postgresql://workmate:workmate@172.19.0.31:5432/workmate_os  (optional)
"""

import os
import sys
import uuid
import argparse
from datetime import datetime

from sqlalchemy import create_engine, text

# ─── ANSI Farben ─────────────────────────────────────────────────────────────
G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[94m"
DIM = "\033[2m"; RST = "\033[0m"

def ok(msg):   print(f"  {G}✓{RST} {msg}")
def skip(msg): print(f"  {Y}→{RST} {DIM}{msg}{RST}")
def err(msg):  print(f"  {R}✗{RST} {msg}")
def head(msg): print(f"\n{B}▶ {msg}{RST}")

# ─── Konfiguration ────────────────────────────────────────────────────────────
ACCESS_DB = os.getenv("ACCESS_DB", "postgresql://workmate:workmate@172.19.0.31:5432/workmate_access")
OS_DB     = os.getenv("OS_DB",     "postgresql://workmate:workmate@172.19.0.31:5432/workmate_os")

# ─── Simulation-Daten ─────────────────────────────────────────────────────────

ROOM_GROUPS = [
    {"name": "Büroräume", "color": "#6366f1"},
    {"name": "Fahrzeuge", "color": "#f59e0b"},
]

ROOMS = {
    "ag_001": {"id": "buro-haupteingang",  "name": "Büro Hauptzugang",           "description": "Beatusstraße 56 – Haupteingang",     "group": "Büroräume"},
    "ag_002": {"id": "serverraum",         "name": "Serverraum",                 "description": "Zugang nur für technisches Personal", "group": "Büroräume"},
    "ag_003": {"id": "werkstatt-fabian",   "name": "Werkstatt Fabian",           "description": "Fabians Werkstatt",                  "group": "Büroräume"},
    "ag_004": {"id": "content-studio",     "name": "Content Studio",             "description": "Foto / Video / Stream",              "group": "Büroräume"},
    "ag_005": {"id": "fahrzeug-pool",      "name": "Fahrzeug Pool KO-IT-001",    "description": "Toyota Proace City – Poolwagen",      "group": "Fahrzeuge"},
    "ag_006": {"id": "fahrzeug-etienne",   "name": "Fahrzeug Etienne KO-IT-104", "description": "VW Transporter T6.1 – Etienne",      "group": "Fahrzeuge"},
    "ag_007": {"id": "fahrzeug-sascha",    "name": "Fahrzeug Sascha KO-IT-105",  "description": "BYD Seal 6 DM-i – Sascha",          "group": "Fahrzeuge"},
}

USERS = [
    {"id": "KIT-0001", "workmate_id": "WM-100", "username": "joshua.kuhrau",  "display_name": "Joshua Kuhrau",   "phone": "+491622654262", "role": "admin", "smartcard": "SC-KIT-100", "status": "ACTIVE",   "email": "joshua@kit-it-koblenz.de",  "access_groups": ["ag_001","ag_002","ag_003","ag_004","ag_005"]},
    {"id": "KIT-0002", "workmate_id": "WM-101", "username": "jessica.kuhrau", "display_name": "Jessica Kuhrau",  "phone": "+491620000002", "role": "admin", "smartcard": "SC-KIT-101", "status": "ACTIVE",   "email": "jessica@kit-it-koblenz.de", "access_groups": ["ag_001","ag_004","ag_005"]},
    {"id": "KIT-0003", "workmate_id": "WM-102", "username": "lena.hoffmann",  "display_name": "Lena Hoffmann",   "phone": "+491620000003", "role": "user",  "smartcard": "SC-KIT-102", "status": "ACTIVE",   "email": "lena@kit-it-koblenz.de",    "access_groups": ["ag_001","ag_004","ag_005"]},
    {"id": "KIT-0004", "workmate_id": "WM-103", "username": "fabian.weber",   "display_name": "Fabian Weber",    "phone": "+491620000004", "role": "admin", "smartcard": "SC-KIT-103", "status": "ACTIVE",   "email": "fabian@kit-it-koblenz.de",  "access_groups": ["ag_001","ag_002","ag_003","ag_004","ag_005"]},
    {"id": "KIT-0005", "workmate_id": "WM-104", "username": "etienne.goeken", "display_name": "Etienne Göken",   "phone": "+491620000005", "role": "user",  "smartcard": "SC-KIT-104", "status": "ACTIVE",   "email": "etienne@kit-it-koblenz.de", "access_groups": ["ag_001","ag_004","ag_005","ag_006"]},
    {"id": "KIT-0006", "workmate_id": "WM-105", "username": "sascha.mueller", "display_name": "Sascha Müller",   "phone": "+491620000006", "role": "user",  "smartcard": "SC-KIT-105", "status": "ACTIVE",   "email": "sascha@kit-it-koblenz.de",  "access_groups": ["ag_001","ag_004","ag_005","ag_007"]},
    {"id": "KIT-0007", "workmate_id": "WM-106", "username": "tobias.wenzel",  "display_name": "Tobias Wenzel",   "phone": "+491620000007", "role": "user",  "smartcard": "SC-KIT-106", "status": "PENDING",  "email": "tobias@kit-it-koblenz.de",  "access_groups": []},
    {"id": "KIT-0008", "workmate_id": "WM-107", "username": "amir.hosseini",  "display_name": "Amir Hosseini",   "phone": "+491620000008", "role": "user",  "smartcard": None,          "status": "PENDING",  "email": "amir@kit-it-koblenz.de",    "access_groups": []},
    {"id": "KIT-0009", "workmate_id": "WM-108", "username": "guelcan.yilmaz", "display_name": "Gülcan Yilmaz",   "phone": "+491620000009", "role": "user",  "smartcard": "SC-KIT-108", "status": "PENDING",  "email": "guelcan@kit-it-koblenz.de", "access_groups": []},
]

DEPARTMENTS = [
    "Geschäftsführung", "Operations", "Finance", "Technology",
    "Facility & Event IT", "Event IT", "IT Außendienst", "Marketing",
]

EMPLOYMENT_MAP = {
    "KIT-0001": "OWNER",       "KIT-0002": "PARTNER",
    "KIT-0003": "SHAREHOLDER", "KIT-0004": "SHAREHOLDER",
    "KIT-0005": "EMPLOYEE",    "KIT-0006": "EMPLOYEE",
    "KIT-0007": "WERKSTUDENT", "KIT-0008": "FREELANCER",
    "KIT-0009": "PRAKTIKUM",
}

DEPT_OF_USER = {
    "KIT-0001": "Geschäftsführung",  "KIT-0002": "Operations",
    "KIT-0003": "Finance",           "KIT-0004": "Technology",
    "KIT-0005": "Facility & Event IT", "KIT-0006": "Event IT",
    "KIT-0007": "IT Außendienst",    "KIT-0008": "Technology",
    "KIT-0009": "Marketing",
}

HIRE_DATE = {
    "KIT-0001": "2025-05-01", "KIT-0002": "2025-05-01",
    "KIT-0003": "2027-01-01", "KIT-0004": "2027-01-01",
    "KIT-0005": "2031-05-12", "KIT-0006": "2028-03-01",
    "KIT-0007": "2031-05-19", "KIT-0008": "2031-05-19",
    "KIT-0009": "2031-05-14",
}

EMPLOYMENT_TYPE_OS = {
    "OWNER": "fulltime", "PARTNER": "fulltime", "SHAREHOLDER": "fulltime",
    "EMPLOYEE": "fulltime", "WERKSTUDENT": "parttime",
    "FREELANCER": "external", "PRAKTIKUM": "intern",
}

# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def kc_uuid(user_id: str) -> str:
    """Deterministischer Platzhalter-UUID bis echte KC-UUIDs gesetzt werden."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"kit.{user_id}"))

def exists(conn, table: str, col: str, val: str) -> bool:
    return conn.execute(text(f"SELECT 1 FROM {table} WHERE {col} = :v"), {"v": val}).fetchone() is not None

# ─── workmate-access seeden ───────────────────────────────────────────────────

def seed_access(engine, dry_run: bool):
    now = datetime.utcnow()
    group_name_to_id: dict[str, int] = {}

    with engine.begin() as conn:

        # 1. Raum-Gruppen
        head("Raum-Gruppen")
        for rg in ROOM_GROUPS:
            row = conn.execute(text("SELECT id FROM room_groups WHERE name = :n"), {"n": rg["name"]}).fetchone()
            if row:
                group_name_to_id[rg["name"]] = row[0]
                skip(f"Bereits vorhanden: {rg['name']}")
                continue
            if dry_run:
                skip(f"[dry-run] {rg['name']}")
                continue
            r = conn.execute(text(
                "INSERT INTO room_groups (name, color, created_at) VALUES (:n, :c, :t) RETURNING id"
            ), {"n": rg["name"], "c": rg["color"], "t": now})
            group_name_to_id[rg["name"]] = r.fetchone()[0]
            ok(f"Raum-Gruppe: {rg['name']}")

        # 2. Räume
        head("Räume")
        for ag_id, room in ROOMS.items():
            if exists(conn, "rooms", "id", room["id"]):
                skip(f"Bereits vorhanden: {room['name']}")
                continue
            gid = group_name_to_id.get(room["group"])
            if dry_run:
                skip(f"[dry-run] Raum: {room['name']}")
                continue
            conn.execute(text("""
                INSERT INTO rooms (id, name, description, group_id, is_active, created_at)
                VALUES (:id, :name, :desc, :gid, true, :t)
            """), {"id": room["id"], "name": room["name"], "desc": room["description"], "gid": gid, "t": now})
            ok(f"Raum: {room['name']}")

        # 3. Benutzer
        head("Benutzer")
        for u in USERS:
            if exists(conn, "users", "id", u["id"]):
                skip(f"Bereits vorhanden: {u['display_name']}")
                continue
            if dry_run:
                skip(f"[dry-run] User: {u['display_name']} ({u['id']} / {u['workmate_id']})")
                continue
            conn.execute(text("""
                INSERT INTO users
                    (id, workmate_id, keycloak_id, username, display_name,
                     phone_number, role, is_active, created_at, updated_at)
                VALUES
                    (:id, :wid, :kc, :uname, :dname,
                     :phone, :role, :active, :t, :t)
            """), {
                "id":     u["id"],
                "wid":    u["workmate_id"],
                "kc":     kc_uuid(u["id"]),
                "uname":  u["username"],
                "dname":  u["display_name"],
                "phone":  u["phone"],
                "role":   u["role"],
                "active": u["status"] == "ACTIVE",
                "t":      now,
            })
            ok(f"User: {u['display_name']} ({u['id']} / {u['workmate_id']})")

        # 4. NFC-Chips
        head("NFC-Chips (Smartcards)")
        for u in USERS:
            if not u["smartcard"]:
                skip(f"Kein Smartcard: {u['display_name']} (Freelancer)")
                continue
            if u["status"] != "ACTIVE":
                skip(f"PENDING — kein Chip angelegt: {u['display_name']}")
                continue
            if exists(conn, "nfc_chips", "chip_uid", u["smartcard"]):
                skip(f"Bereits vorhanden: {u['smartcard']}")
                continue
            if dry_run:
                skip(f"[dry-run] Chip {u['smartcard']} → {u['display_name']}")
                continue
            conn.execute(text("""
                INSERT INTO nfc_chips (user_id, chip_uid, label, is_active, created_at)
                VALUES (:uid, :chip, :label, true, :t)
            """), {"uid": u["id"], "chip": u["smartcard"], "label": f"Smartcard {u['smartcard']}", "t": now})
            ok(f"Chip {u['smartcard']} → {u['display_name']}")

        # 5. Berechtigungen
        head("Berechtigungen")
        for u in USERS:
            if not u["access_groups"]:
                skip(f"Keine Berechtigungen: {u['display_name']} (status: {u['status']})")
                continue
            for ag_id in u["access_groups"]:
                room = ROOMS[ag_id]
                already = conn.execute(text(
                    "SELECT 1 FROM permissions WHERE user_id=:u AND room_id=:r AND is_active=true"
                ), {"u": u["id"], "r": room["id"]}).fetchone()
                if already:
                    skip(f"Bereits vorhanden: {u['id']} → {room['name']}")
                    continue
                if dry_run:
                    skip(f"[dry-run] {u['id']} → {room['name']}")
                    continue
                conn.execute(text("""
                    INSERT INTO permissions
                        (user_id, room_id, access_level, is_active, created_at)
                    VALUES (:uid, :rid, 'read', true, :t)
                """), {"uid": u["id"], "rid": room["id"], "t": now})
                ok(f"{u['id']} → {room['name']}")


# ─── workmate-os seeden ───────────────────────────────────────────────────────

def seed_os(engine, dry_run: bool):
    now = datetime.utcnow()
    dept_name_to_id: dict[str, str] = {}

    with engine.begin() as conn:

        # 1. Abteilungen
        head("Abteilungen (workmate-os)")
        for dept in DEPARTMENTS:
            row = conn.execute(text("SELECT id FROM departments WHERE name = :n"), {"n": dept}).fetchone()
            if row:
                dept_name_to_id[dept] = str(row[0])
                skip(f"Bereits vorhanden: {dept}")
                continue
            if dry_run:
                skip(f"[dry-run] Abteilung: {dept}")
                continue
            r = conn.execute(text(
                "INSERT INTO departments (id, name, created_at) VALUES (gen_random_uuid(), :n, :t) RETURNING id"
            ), {"n": dept, "t": now})
            dept_name_to_id[dept] = str(r.fetchone()[0])
            ok(f"Abteilung: {dept}")

        # 2. Mitarbeiter
        head("Mitarbeiter (workmate-os)")
        for u in USERS:
            row = conn.execute(text(
                "SELECT id FROM employees WHERE employee_code = :c"
            ), {"c": u["id"]}).fetchone()
            if row:
                # workmate_id nachtragen falls noch nicht gesetzt
                conn.execute(text(
                    "UPDATE employees SET workmate_id = :wid WHERE employee_code = :c AND workmate_id IS NULL"
                ), {"wid": u["workmate_id"], "c": u["id"]})
                skip(f"Bereits vorhanden: {u['display_name']} (workmate_id aktualisiert)")
                continue
            dept_id = dept_name_to_id.get(DEPT_OF_USER[u["id"]])
            emp_type = EMPLOYMENT_TYPE_OS.get(EMPLOYMENT_MAP[u["id"]], "fulltime")
            if dry_run:
                skip(f"[dry-run] Mitarbeiter: {u['display_name']} ({u['id']} / {u['workmate_id']})")
                continue
            conn.execute(text("""
                INSERT INTO employees
                    (id, employee_code, workmate_id, uuid_keycloak,
                     first_name, last_name, email, phone,
                     employment_type, department_id, hire_date,
                     status, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :code, :wid, :kc,
                     :fn, :ln, :email, :phone,
                     :etype, :dept, :hire,
                     :status, :t, :t)
            """), {
                "code":   u["id"],
                "wid":    u["workmate_id"],
                "kc":     kc_uuid(u["id"]),
                "fn":     u["display_name"].split()[0],
                "ln":     " ".join(u["display_name"].split()[1:]),
                "email":  u["email"],
                "phone":  u["phone"],
                "etype":  emp_type,
                "dept":   dept_id,
                "hire":   HIRE_DATE[u["id"]],
                "status": "active" if u["status"] == "ACTIVE" else "inactive",
                "t":      now,
            })
            ok(f"Mitarbeiter: {u['display_name']} ({u['id']} / {u['workmate_id']})")


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
    print(f"  ACCESS_DB : {ACCESS_DB.split('@')[-1]}")
    print(f"  OS_DB     : {OS_DB.split('@')[-1]}")

    if not args.skip_access:
        print(f"\n{'─'*55}")
        print(f"  workmate-access")
        print(f"{'─'*55}")
        try:
            engine = create_engine(ACCESS_DB)
            seed_access(engine, args.dry_run)
        except Exception as e:
            err(f"workmate-access fehlgeschlagen: {e}")
            raise

    if not args.skip_os:
        print(f"\n{'─'*55}")
        print(f"  workmate-os")
        print(f"{'─'*55}")
        try:
            engine = create_engine(OS_DB)
            seed_os(engine, args.dry_run)
        except Exception as e:
            err(f"workmate-os fehlgeschlagen: {e}")

    print(f"\n{'='*55}")
    print(f"  {G}Fertig!{RST}")
    if args.dry_run:
        print(f"  Ohne --dry-run um wirklich zu schreiben.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
