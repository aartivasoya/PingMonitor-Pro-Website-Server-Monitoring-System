import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import DB_PATH

__all__ = [
    "get_connection",
    "init_db",
    "add_website",
    "get_websites",
    "get_favorites",
    "toggle_favorite",
    "get_website",
    "record_check",
    "get_recent_checks",
    "get_dashboard_stats",
    "add_user",
    "get_user",
    "list_users",
    "log_activity",
    "get_activity_logs",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS websites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            check_interval INTEGER DEFAULT 60,
            alert_email TEXT,
            favorite INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website_id INTEGER NOT NULL,
            checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            response_time_ms REAL,
            details TEXT,
            FOREIGN KEY (website_id) REFERENCES websites(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()

    # Migrations: ensure newer columns exist in existing databases
    def _has_column(table: str, column: str) -> bool:
        cur = conn.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        return column in cols

    # Add 'favorite' column to 'websites' if missing
    if not _has_column("websites", "favorite"):
        try:
            conn.execute("ALTER TABLE websites ADD COLUMN favorite INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            # if this fails, continue — app will surface clearer error
            pass

    conn.close()


def add_website(name: str, url: str, check_interval: int = 60, alert_email: str = "") -> Tuple[int, bool]:
    """Add a website. Returns (website_id, created).

    If a website with the same URL already exists, returns its id and
    created=False. Otherwise inserts and returns new id and created=True.
    """
    conn = get_connection()
    cur = conn.cursor()
    # Check for existing URL first to avoid IntegrityError bubbling up
    existing = cur.execute("SELECT id FROM websites WHERE url = ?", (url,)).fetchone()
    if existing:
        website_id = existing[0]
        conn.close()
        return website_id, False

    try:
        cur.execute(
            "INSERT INTO websites (name, url, check_interval, alert_email) VALUES (?, ?, ?, ?)",
            (name, url, check_interval, alert_email),
        )
        conn.commit()
        website_id = cur.lastrowid
        conn.close()
        return website_id, True
    except Exception:
        # On unexpected failure, attempt to return existing id if present
        existing = cur.execute("SELECT id FROM websites WHERE url = ?", (url,)).fetchone()
        conn.close()
        if existing:
            return existing[0], False
        raise


def get_websites(search: str = "", *args, **kwargs) -> List[Dict[str, Any]]:
    # Accept positional or keyword search for backwards compatibility.
    if args:
        # first positional arg treated as search
        search = args[0]
    conn = get_connection()
    query = "SELECT id, name, url, check_interval, alert_email, favorite, created_at FROM websites"
    params: List[Any] = []
    if search:
        query += " WHERE lower(name) LIKE ? OR lower(url) LIKE ?"
        like = f"%{search.lower()}%"
        params.extend([like, like])
    query += " ORDER BY favorite DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_favorites() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, url, check_interval, alert_email, favorite, created_at FROM websites WHERE favorite = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def toggle_favorite(website_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE websites SET favorite = CASE WHEN favorite = 1 THEN 0 ELSE 1 END WHERE id = ?", (website_id,))
    conn.commit()
    conn.close()


def get_website(website_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, name, url, check_interval, alert_email, favorite, created_at FROM websites WHERE id = ?",
        (website_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def record_check(website_id: int, status: str, response_time_ms: Optional[float], details: str = "") -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO checks (website_id, checked_at, status, response_time_ms, details) VALUES (?, ?, ?, ?, ?)",
        (website_id, datetime.utcnow().isoformat(), status, response_time_ms, details),
    )
    conn.commit()
    conn.close()


def get_recent_checks(website_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    if website_id is None:
        rows = conn.execute(
            "SELECT c.id, c.website_id, c.checked_at, c.status, c.response_time_ms, c.details, w.name AS website_name FROM checks c JOIN websites w ON w.id = c.website_id ORDER BY c.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT c.id, c.website_id, c.checked_at, c.status, c.response_time_ms, c.details, w.name AS website_name FROM checks c JOIN websites w ON w.id = c.website_id WHERE c.website_id = ? ORDER BY c.id DESC LIMIT ?",
            (website_id, limit),
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_connection()
    websites = conn.execute("SELECT COUNT(*) AS count FROM websites").fetchone()["count"]
    checks = conn.execute("SELECT COUNT(*) AS count FROM checks").fetchone()["count"]
    up_checks = conn.execute("SELECT COUNT(*) AS count FROM checks WHERE status = 'up'").fetchone()["count"]
    conn.close()
    return {
        "sites": websites,
        "checks": checks,
        "up_checks": up_checks,
        "availability": round((up_checks / checks) * 100, 1) if checks else 100.0,
    }


def add_user(username: str, password: str, role: str = "viewer") -> Tuple[int, bool]:
    """Add a user. Returns (user_id, created).

    If `username` already exists, returns its id and created=False.
    """
    conn = get_connection()
    cur = conn.cursor()
    existing = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        user_id = existing[0]
        conn.close()
        return user_id, False

    try:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return user_id, True
    except Exception:
        existing = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if existing:
            return existing[0], False
        raise


def get_user(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT id, username, password, role, created_at FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_activity(username: str, action: str, details: str = "") -> None:
    conn = get_connection()
    conn.execute("INSERT INTO activity_logs (username, action, details) VALUES (?, ?, ?)", (username, action, details))
    conn.commit()
    conn.close()


def get_activity_logs(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT id, username, action, details, created_at FROM activity_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


init_db()
