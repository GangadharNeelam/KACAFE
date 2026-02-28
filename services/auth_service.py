"""Authentication service — credential validation."""
from __future__ import annotations
from werkzeug.security import check_password_hash
from database.db import get_connection


def authenticate(username: str, password: str) -> dict | None:
    """Validate credentials. Returns user dict on success, None on failure."""
    if not username or not password:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
    user = cur.fetchone()
    conn.close()
    if user and check_password_hash(user["password_hash"], password):
        return {"id": user["id"], "username": user["username"], "role": user["role"]}
    return None
