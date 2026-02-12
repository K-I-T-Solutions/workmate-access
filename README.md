# workmate-access

Workmate Access ist ein Tool für die Verwaltung und Controlling unseres Zugangssystems.

## Projektstruktur

```
workmate-access/
├── backend/       ← FastAPI-Backend (Server)
│   ├── app/
│   ├── migrations/
│   ├── alembic.ini
│   ├── Makefile
│   └── requirements.txt
├── firmware/      ← ESP32-Firmware (Client, PlatformIO)
│   ├── include/
│   ├── src/
│   ├── lib/
│   ├── test/
│   └── platformio.ini
└── README.md
```

## Backend

FastAPI-Server mit PostgreSQL und Alembic-Migrations.

```bash
cd backend
source ../.venv/bin/activate
make run  # oder: uvicorn app.main:app --reload --port 8000
```

## Firmware

ESP32-Firmware mit PlatformIO. Verwaltet NFC-Chip-Lesung und kommuniziert mit dem Backend.

```bash
cd firmware
cp include/secrets.h.example include/secrets.h  # Credentials eintragen
pio run
```
