# Workmate Access - Next Steps

## Kritisch

- [ ] **Authentifizierung implementieren** - Alle Endpoints sind komplett offen. Zitadel-Config existiert in `app/core/config.py`, wird aber nirgends eingebunden. Auth-Middleware/Dependency für FastAPI erstellen.
- [ ] **CORS-Config fixen** - Default `CORS_ORIGINS = '*'` wird mit `json.loads()` geparsed und crasht. Muss ein gültiges JSON-Array sein (z.B. `'["http://localhost:8000"]'`) oder Wildcard separat behandeln.
- [ ] **Unique-Constraint auf Permissions** - Kein Unique-Constraint auf `(user_id, room_id)` in der `permissions`-Tabelle. Erlaubt doppelte Einträge. Alembic-Migration hinzufügen.

## Hoch

- [ ] **Tests schreiben** - Null Testabdeckung. `pytest` + `httpx` als Dev-Dependencies hinzufügen, Tests für Access-Service, Card-Verify und Rate-Limiting.
- [ ] **Indexes auf `access_logs`** - Fehlende Indexes auf `nfc_chip_id`, `user_id`, `timestamp`, `granted`. Der Lockout-Check (`_is_locked_out`) macht sonst Full-Table-Scans. Alembic-Migration erstellen.
- [ ] **Pagination für Logs** - `GET /api/v1/access/logs` hat `limit=100` aber kein Offset/Cursor. Bei vielen Einträgen unbrauchbar.
- [ ] **Info-Leak bei Card-Response** - `CardVerifyResponse` gibt `user_name` bei fehlgeschlagenen Versuchen zurück. Ermöglicht Card-Enumeration. Bei `access=False` keine User-Daten zurückgeben.

## Mittel

- [ ] **Deprecated `.dict()` ersetzen** - In `app/api/routes/permissions.py` noch `.dict()` statt `.model_dump()` (Pydantic v2).
- [ ] **`access_level` als Enum validieren** - Wird als freier String gespeichert, jeder Wert geht. Sollte auf definierte Werte (`read`, `write`, `admin`) beschränkt sein.
- [ ] **Error-Handling bei DB-Fehlern** - Wenn `db.commit()` fehlschlägt, gibt's einen ungefangenen 500er. Try/Except mit sinnvollen HTTP-Responses.
- [ ] **`Base.metadata.create_all()` entfernen** - In `app/main.py` wird `create_all()` neben Alembic genutzt. Kann zu Konflikten führen, besser nur Alembic.
- [ ] **`role`-Feld im User-Model validieren** - Kein Enum, jeder String wird akzeptiert. Sollte auf `user`/`admin` beschränkt sein.
