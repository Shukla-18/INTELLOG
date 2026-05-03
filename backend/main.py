"""Intellog Backend - FastAPI Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.database import init_db, SessionLocal
from backend.routes import router
from backend.cloud_routes import cloud_router
from backend.auth import create_default_admin

app = FastAPI(
    title="Intellog - Cybersecurity Monitoring System",
    description="Real-time cloud VM monitoring, threat detection, and reporting",
    version="1.0.0",
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")
app.include_router(cloud_router, prefix="/api")

# Serve frontend static files (MUST be after API routes)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.on_event("startup")
def startup():
    """Initialize DB and create default admin on startup."""
    init_db()
    db = SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()


@app.get("/api/health")
def health_check():
    return {"status": "online", "service": "Intellog Backend"}
