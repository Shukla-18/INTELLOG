"""Intellog Backend - FastAPI Main Application"""
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
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

# ========== NO-CACHE MIDDLEWARE ==========
# Prevents browser and Cloudflare from serving stale files
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    # No-cache for HTML, JS, CSS, and API responses
    path = request.url.path
    if path.endswith((".html", ".js", ".css")) or path.startswith("/api") or path == "/":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Include API routes
app.include_router(router, prefix="/api")
app.include_router(cloud_router, prefix="/api")

# ========== FRONTEND SERVING ==========
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

# Serve index.html with cache-busting at root
@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serve index.html with cache-busting query params on assets."""
    index_path = frontend_dir / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)

    html = index_path.read_text(encoding="utf-8")

    # Inject cache-busting version into JS/CSS references
    version = str(int(time.time()))
    html = html.replace('src="app.js"', f'src="app.js?v={version}"')
    html = html.replace('href="styles.css"', f'href="styles.css?v={version}"')

    return HTMLResponse(content=html)

# Mount static files for JS/CSS/images (after root route)
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=False), name="frontend")


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
    return {"status": "online", "service": "Intellog Backend", "version": "1.0.0"}
