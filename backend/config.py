"""Intellog Backend Configuration"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "intellog.db"
CSV_DIR = DATA_DIR / "csv_exports"
REPORTS_DIR = BASE_DIR / "reports" / "generated"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
CSV_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Auth
SECRET_KEY = os.getenv("INTELLOG_SECRET_KEY", "intellog-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Filtering thresholds
CPU_THRESHOLD = 80.0
MEMORY_THRESHOLD = 85.0
NETWORK_SPIKE_THRESHOLD = 1_000_000  # bytes/sec
FAILED_LOGIN_THRESHOLD = 5

# Default admin credentials
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "intellog2024"
