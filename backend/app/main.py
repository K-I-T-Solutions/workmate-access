from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .api.routes import access, rooms, room_groups, users, permissions, nfc_chips, yubikeys

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title=settings.PROJEKT_NAME,
    version=settings.VERSION,
    description="Ein dezentrales Orchestrator für ein Zugangsystem"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(access.router)
app.include_router(rooms.router)
app.include_router(room_groups.router)
app.include_router(users.router)
app.include_router(permissions.router)
app.include_router(nfc_chips.router)
app.include_router(yubikeys.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/config")
def frontend_config():
    return {
        "keycloak_url": settings.KEYCLOAK_URL,
        "keycloak_realm": settings.KEYCLOAK_REALM,
        "keycloak_client_id": settings.KEYCLOAK_CLIENT_ID,
    }