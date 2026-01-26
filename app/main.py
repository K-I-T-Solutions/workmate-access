from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .db.database import engine
from .models import Base
from .api.routes import access, rooms, users, permissions

# Create tables
Base.metadata.create_all(bind=engine)

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
app.include_router(users.router)
app.include_router(permissions.router)

@app.get("/")
def read_root():
    return {"ok": True, "msg": "Workmate Access", "version": settings.VERSION}

@app.get("/health")
def health():
    return {"status": "healthy"}