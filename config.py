import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "pingmonitor.db"
ASSETS_DIR = BASE_DIR / "assets"
CSS_PATH = ASSETS_DIR / "css.css"

APP_TITLE = "PingMonitor Pro"
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
