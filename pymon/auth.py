"""JWT Authentication module for PyMon"""

import hashlib
import os
import secrets
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from pymon.api.deps import get_db


def _load_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret
    secret_file = os.path.join(os.path.dirname(__file__), "..", ".pymon_jwt_secret")
    secret_file = os.path.normpath(secret_file)
    try:
        with open(secret_file) as f:
            stored = f.read().strip()
            if stored:
                return stored
    except (FileNotFoundError, OSError):
        pass
    new_secret = secrets.token_urlsafe(32)
    try:
        with open(secret_file, "w") as f:
            f.write(new_secret)
        os.chmod(secret_file, 0o600)
    except OSError as e:
        # Could not persist the secret: every restart will now invalidate all tokens.
        # Surface this loudly instead of failing silently; set JWT_SECRET env to fix.
        print(
            f"WARNING: could not persist JWT secret to {secret_file} ({e}). "
            "Tokens will be invalidated on restart. Set the JWT_SECRET environment variable "
            "to a fixed value to avoid this.",
            file=sys.stderr,
        )
    return new_secret


JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


class User(BaseModel):
    id: int
    username: str
    is_admin: bool = False
    must_change_password: bool = False
    # How the principal authenticated: "jwt" (interactive login) or "api_key".
    # API-key principals are never allowed to perform admin actions.
    auth_method: str = "jwt"


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class APIKeyCreate(BaseModel):
    name: str


@dataclass
class AuthConfig:
    db_path: str = "pymon.db"
    admin_username: str = "admin"
    admin_password: str = ""


def _load_auth_config() -> AuthConfig:
    """Load auth config from YAML config file, falling back to defaults."""
    from pymon.config import load_config
    try:
        config = load_config(os.getenv("CONFIG_PATH", "config.yml"))
        if hasattr(config, 'auth') and config.auth:
            admin_password = getattr(config.auth, 'admin_password', '')
            # If the password is empty or a known weak default, generate a strong
            # random one (overridable via the PYMON_ADMIN_PASSWORD env var).
            if not admin_password or admin_password in ('change-me-on-first-login', '291263'):
                admin_password = os.environ.get("PYMON_ADMIN_PASSWORD") or secrets.token_urlsafe(18)
            return AuthConfig(
                admin_username=getattr(config.auth, 'admin_username', 'admin'),
                admin_password=admin_password,
            )
    except Exception:
        pass
    # Never fall back to a hardcoded password — always generate a strong random one
    return AuthConfig(
        admin_password=os.environ.get("PYMON_ADMIN_PASSWORD") or secrets.token_urlsafe(18)
    )


auth_config = _load_auth_config()


def _log_audit(user_id: int, action: str, details: str = "", ip_address: str = ""):
    conn = None
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, details, ip_address, timestamp) VALUES (?, ?, ?, ?, ?)",
            (user_id, action, details, ip_address, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        if conn is not None:
            conn.close()


def init_auth_tables():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0,
        must_change_password BOOLEAN DEFAULT 1,
        created_at TEXT,
        last_login TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        key_hash TEXT NOT NULL,
        name TEXT,
        created_at TEXT,
        last_used TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # Migration: add indexed sha256 lookup so validate_api_key does an O(1) exact
    # match instead of a bcrypt scan over every row (DoS + timing-leak vector).
    try:
        c.execute("PRAGMA table_info(api_keys)")
        key_cols = {row[1] for row in c.fetchall()}
        if "key_sha256" not in key_cols:
            c.execute("ALTER TABLE api_keys ADD COLUMN key_sha256 TEXT")
        c.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_sha256 ON api_keys(key_sha256)")
    except Exception:
        pass

    c.execute("SELECT id FROM users WHERE username = ?", (auth_config.admin_username,))
    admin_row = c.fetchone()

    if not admin_row:
        # First run only: create the admin and show the generated password ONCE.
        # The password is never persisted in cleartext anywhere — only the bcrypt
        # hash is stored. If it is lost, use the `reset-admin` CLI command.
        password = auth_config.admin_password
        c.execute(
            "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at) "
            "VALUES (?, ?, 1, 1, ?)",
            (auth_config.admin_username, hash_password(password), datetime.now(timezone.utc).isoformat()),
        )
        msg = (
            f"\n{'='*60}\n"
            f"DEFAULT ADMIN USER CREATED — this password is shown ONLY now.\n"
            f"Username: {auth_config.admin_username}\n"
            f"Password: {password}\n"
            f"Store it in a password manager and change it after first login.\n"
            f"{'='*60}\n"
        )
        print(msg)
    else:
        print(f"[OK] Admin user '{auth_config.admin_username}' already exists\n")

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _token_expire_hours() -> int:
    """Configured JWT lifetime (config.auth.jwt_expire_hours), default 24."""
    try:
        from pymon.config import get_cached_config

        return int(get_cached_config().auth.jwt_expire_hours)
    except Exception:
        return JWT_EXPIRE_HOURS


def create_token(user_id: int, username: str, is_admin: bool, must_change: bool) -> str:
    payload = {
        "sub": username,
        "user_id": user_id,
        "is_admin": is_admin,
        "must_change_password": must_change,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_token_expire_hours()),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    # Sync dependency: FastAPI runs it in a threadpool, keeping the blocking
    # sqlite/bcrypt work off the event loop.
    if not credentials:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return validate_api_key(api_key)
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, is_admin, must_change_password FROM users WHERE username = ?", (payload["sub"],))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    return User(
        id=row["id"],
        username=row["username"],
        is_admin=bool(row["is_admin"]),
        must_change_password=bool(row["must_change_password"]),
    )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    # API keys are for ingestion/read only — they can never perform admin actions,
    # regardless of the owning user's role.
    if current_user.auth_method == "api_key":
        raise HTTPException(status_code=403, detail="API keys cannot perform admin actions")
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def validate_api_key(api_key: str) -> User:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    def _resolve(row, backfill_sha: str | None = None) -> Optional[User]:
        """Confirm the bcrypt hash, touch last_used, and return the owning user."""
        if not verify_password(api_key, row["key_hash"]):
            return None
        if backfill_sha is not None:
            c.execute("UPDATE api_keys SET last_used = ?, key_sha256 = ? WHERE id = ?", (now, backfill_sha, row["id"]))
        else:
            c.execute("UPDATE api_keys SET last_used = ? WHERE id = ?", (now, row["id"]))
        conn.commit()
        c.execute("SELECT id, username, is_admin, must_change_password FROM users WHERE id = ?", (row["user_id"],))
        user = c.fetchone()
        if not user:
            return None
        return User(
            id=user["id"],
            username=user["username"],
            is_admin=bool(user["is_admin"]),
            must_change_password=bool(user["must_change_password"]),
            auth_method="api_key",
        )

    try:
        # Fast path: indexed exact match on the sha256 lookup (no per-row bcrypt scan).
        sha = _api_key_sha256(api_key)
        row = c.execute("SELECT id, user_id, key_hash FROM api_keys WHERE key_sha256 = ?", (sha,)).fetchone()
        if row is not None:
            user = _resolve(row)
            if user is not None:
                return user

        # Legacy fallback: keys created before the migration have no sha256 yet.
        # Scan only those, and backfill the sha256 on the matched row so it migrates.
        for legacy in c.execute(
            "SELECT id, user_id, key_hash FROM api_keys WHERE key_sha256 IS NULL"
        ).fetchall():
            user = _resolve(legacy, backfill_sha=sha)
            if user is not None:
                return user
    finally:
        conn.close()

    raise HTTPException(status_code=401, detail="Invalid API key")


def create_user(username: str, password: str, is_admin: bool = False) -> User:
    conn = get_db()
    c = conn.cursor()

    try:
        password_hash = hash_password(password)
        c.execute(
            "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at) VALUES (?, ?, ?, 1, ?)",
            (username, password_hash, int(is_admin), datetime.now(timezone.utc).isoformat()),
        )
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        _log_audit(user_id, "User Created", f"Created user '{username}' (admin={is_admin})")
        return User(id=user_id, username=username, is_admin=is_admin, must_change_password=True)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")


def authenticate_user(username: str, password: str) -> Token:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, username, password_hash, is_admin, must_change_password FROM users WHERE username = ?", (username,)
    )
    row = c.fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), row["id"]),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

    user = User(
        id=row["id"],
        username=row["username"],
        is_admin=bool(row["is_admin"]),
        must_change_password=bool(row["must_change_password"]),
    )

    token = create_token(user.id, user.username, user.is_admin, user.must_change_password)
    _log_audit(user.id, "Login", f"User '{username}' logged in")
    return Token(access_token=token, user=user)


def validate_password_complexity(password: str) -> None:
    """Shared password policy: >=12 chars with upper, lower and digit.

    Raises HTTPException(400) on failure. Used by every password-setting path so
    the policy can't drift between endpoints.
    """
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters")
    if not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain uppercase, lowercase, and digit")


def set_password(user_id: int, new_password: str) -> bool:
    """Admin-only: set a user's password without requiring current password."""
    validate_password_complexity(new_password)
    conn = get_db()
    c = conn.cursor()
    new_hash = hash_password(new_password)
    c.execute("UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?", (new_hash, user_id))
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit()
    conn.close()
    _log_audit(user_id, "Password Changed", "Admin reset password")
    return True


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    # Validate the new password BEFORE opening a connection so a policy failure
    # can't leak the DB handle.
    validate_password_complexity(new_password)

    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()

    if not row or not verify_password(current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = hash_password(new_password)
    c.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    _log_audit(user_id, "Password Changed", "User changed own password")
    return True


def _api_key_sha256(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_api_key(user_id: int, name: str) -> str:
    api_key = f"pymon_{secrets.token_urlsafe(32)}"
    key_hash = hash_password(api_key)

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO api_keys (user_id, key_hash, key_sha256, name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, key_hash, _api_key_sha256(api_key), name, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    _log_audit(user_id, "API Key Created", f"Created key '{name}'")

    return api_key


def list_api_keys(user_id: int) -> list[dict]:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, name, created_at, last_used FROM api_keys WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r["id"], "name": r["name"], "created_at": r["created_at"], "last_used": r["last_used"]} for r in rows
    ]


def delete_api_key(user_id: int, key_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
    deleted: bool = bool(c.rowcount)
    conn.commit()
    conn.close()
    _log_audit(user_id, "API Key Deleted", f"Deleted key id={key_id}")
    return deleted


def list_users() -> list[dict]:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, is_admin, must_change_password, created_at, last_login FROM users ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "username": r["username"],
            "is_admin": bool(r["is_admin"]),
            "must_change_password": bool(r["must_change_password"]),
            "created_at": r["created_at"],
            "last_login": r["last_login"],
        }
        for r in rows
    ]


def _count_admins(c) -> int:
    return c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]


def update_user(user_id: int, is_admin: Optional[bool] = None, must_change_password: Optional[bool] = None) -> bool:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if is_admin is False:
        # Block demoting the last remaining admin (would lock everyone out).
        row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        if row and row["is_admin"] and _count_admins(c) <= 1:
            conn.close()
            raise HTTPException(status_code=400, detail="Cannot demote the last admin user")
    if is_admin is not None:
        c.execute("UPDATE users SET is_admin = ? WHERE id = ?", (int(is_admin), user_id))
    if must_change_password is not None:
        c.execute("UPDATE users SET must_change_password = ? WHERE id = ?", (int(must_change_password), user_id))
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    _log_audit(user_id, "User Updated", f"Updated user id={user_id}")
    return bool(updated)


def delete_user(user_id: int) -> bool:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    row = c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    # Block deleting the last remaining admin (would lock everyone out).
    if row["is_admin"] and _count_admins(c) <= 1:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot delete the last admin user")
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    _log_audit(user_id, "User Deleted", f"Deleted user id={user_id}")
    return bool(deleted)
