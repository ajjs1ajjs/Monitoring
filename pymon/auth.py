"""JWT Authentication module for PyMon"""

import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from pymon.api.deps import get_db


def _derive_fernet_key(secret: str) -> bytes:
    import base64, hashlib
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def _encrypt_password(plaintext: str, secret: str) -> str:
    if not plaintext:
        return ""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_derive_fernet_key(secret))
        return f.encrypt(plaintext.encode()).decode()
    except Exception:
        return ""


def _decrypt_password(ciphertext: str, secret: str) -> str:
    if not ciphertext:
        return ""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_derive_fernet_key(secret))
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""


def _save_credentials_file(password: str):
    try:
        paths = []
        if os.name == "nt":
            app_dir = os.path.dirname(os.path.abspath(__file__))
            paths.append(os.path.join(app_dir, "..", "credentials.txt"))
            up = os.environ.get("USERPROFILE", "")
            if up:
                paths.append(os.path.join(up, "PyMon", "credentials.txt"))
        else:
            paths.append("/etc/pymon/credentials.txt")
            paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "credentials.txt"))

        for path in paths:
            try:
                path = os.path.normpath(os.path.abspath(path))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(f"Admin password: {password}\n")
                    f.write("Username: admin\n")
                if os.name != "nt":
                    os.chmod(path, 0o600)
            except Exception:
                continue
    except Exception:
        pass


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
    except OSError:
        pass
    return new_secret


JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


class User(BaseModel):
    id: int
    username: str
    is_admin: bool = False
    must_change_password: bool = False


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
    admin_password: str = "change-me-on-first-login"


def _load_auth_config() -> AuthConfig:
    """Load auth config from YAML config file, falling back to defaults."""
    from pymon.config import load_config
    try:
        config = load_config(os.getenv("CONFIG_PATH", "config.yml"))
        if hasattr(config, 'auth') and config.auth:
            admin_password = getattr(config.auth, 'admin_password', 'change-me-on-first-login')
            # If admin_password is the default, generate random one
            if admin_password in ('change-me-on-first-login', '291263'):
                admin_password = os.environ.get("PYMON_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
            return AuthConfig(
                admin_username=getattr(config.auth, 'admin_username', 'admin'),
                admin_password=admin_password,
            )
    except Exception:
        pass
    return AuthConfig()


auth_config = _load_auth_config()


def _log_audit(user_id: int, action: str, details: str = "", ip_address: str = ""):
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, details, ip_address, timestamp) VALUES (?, ?, ?, ?, ?)",
            (user_id, action, details, ip_address, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


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

    # Migration: add password_encrypted column
    try:
        c.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in c.fetchall()}
        if "password_encrypted" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN password_encrypted TEXT")
    except Exception:
        pass

    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        key_hash TEXT NOT NULL,
        name TEXT,
        created_at TEXT,
        last_used TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    jwt_key = JWT_SECRET
    c.execute("SELECT id, password_hash, password_encrypted FROM users WHERE username = ?", (auth_config.admin_username,))
    admin_row = c.fetchone()

    if not admin_row:
        password = auth_config.admin_password
        # If password is the default (291263 or random), use the generated one from auth_config
        password_hash = hash_password(password)
        encrypted = _encrypt_password(password, jwt_key)
        c.execute(
            "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at, password_encrypted) VALUES (?, ?, 1, 1, ?, ?)",
            (auth_config.admin_username, password_hash, datetime.now(timezone.utc).isoformat(), encrypted or None),
        )
        _save_credentials_file(password)
        msg = (
            f"\n{'='*50}\n"
            f"DEFAULT ADMIN USER CREATED\n"
            f"Username: {auth_config.admin_username}\n"
            f"Password: {password}\n"
            f"{'='*50}\n"
        )
        print(msg)
    else:
        existing_encrypted = admin_row[2]
        if existing_encrypted:
            saved_pw = _decrypt_password(existing_encrypted, jwt_key)
            if saved_pw:
                print(f"\n{'='*50}\nAdmin user '{auth_config.admin_username}' already exists\nCurrent password: {saved_pw}\n{'='*50}\n")
                _save_credentials_file(saved_pw)
            else:
                print(f"[OK] Admin user '{auth_config.admin_username}' already exists\n")
        else:
            # Legacy admin without encrypted backup — encrypt current password if possible
            try:
                password_hash = admin_row[1]
                # Can't decrypt bcrypt, so just note it
                print(f"[OK] Admin user '{auth_config.admin_username}' already exists (no password backup)\n")
            except Exception:
                pass

    # Update password_encrypted for legacy users if missing
    try:
        c.execute("SELECT id, password_hash FROM users WHERE username = ? AND (password_encrypted IS NULL OR password_encrypted = '')", (auth_config.admin_username,))
        legacy = c.fetchone()
        if legacy:
            # Try to set encrypted backup by checking if the current config password matches
            if verify_password(auth_config.admin_password, legacy[1]):
                encrypted = _encrypt_password(auth_config.admin_password, jwt_key)
                if encrypted:
                    c.execute("UPDATE users SET password_encrypted = ? WHERE id = ?", (encrypted, legacy[0]))
                    _save_credentials_file(auth_config.admin_password)
    except Exception:
        pass

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


def create_token(user_id: int, username: str, is_admin: bool, must_change: bool) -> str:
    payload = {
        "sub": username,
        "user_id": user_id,
        "is_admin": is_admin,
        "must_change_password": must_change,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
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


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), request: Optional[Request] = None
) -> User:
    if not credentials:
        api_key = request.headers.get("X-API-Key") if request else None
        if api_key:
            return await validate_api_key(api_key)
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
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def validate_api_key(api_key: str) -> User:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    for row in c.execute("SELECT user_id, key_hash FROM api_keys"):
        if verify_password(api_key, row["key_hash"]):
            c.execute(
                "UPDATE api_keys SET last_used = ? WHERE user_id = ?",
                (datetime.now(timezone.utc).isoformat(), row["user_id"]),
            )
            conn.commit()

            c.execute("SELECT id, username, is_admin, must_change_password FROM users WHERE id = ?", (row["user_id"],))
            user = c.fetchone()
            conn.close()

            if user:
                return User(id=user["id"], username=user["username"], is_admin=user["is_admin"])

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


def set_password(user_id: int, new_password: str) -> bool:
    """Admin-only: set a user's password without requiring current password."""
    if len(new_password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters")
    if not any(c.isupper() for c in new_password) or not any(c.islower() for c in new_password) or not any(c.isdigit() for c in new_password):
        raise HTTPException(status_code=400, detail="Password must contain uppercase, lowercase, and digit")
    conn = get_db()
    c = conn.cursor()
    new_hash = hash_password(new_password)
    encrypted = _encrypt_password(new_password, JWT_SECRET)
    c.execute("UPDATE users SET password_hash = ?, password_encrypted = ?, must_change_password = 1 WHERE id = ?", (new_hash, encrypted or None, user_id))
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit()
    conn.close()
    _save_credentials_file(new_password)
    _log_audit(user_id, "Password Changed", "Admin reset password")
    return True


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()

    if not row or not verify_password(current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(new_password) < 12:
        conn.close()
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters with uppercase, lowercase, and digit")
    if not any(c.isupper() for c in new_password) or not any(c.islower() for c in new_password) or not any(c.isdigit() for c in new_password):
        conn.close()
        raise HTTPException(status_code=400, detail="Password must contain uppercase, lowercase, and digit")

    new_hash = hash_password(new_password)
    encrypted = _encrypt_password(new_password, JWT_SECRET)
    c.execute("UPDATE users SET password_hash = ?, password_encrypted = ?, must_change_password = 0 WHERE id = ?", (new_hash, encrypted or None, user_id))
    conn.commit()
    conn.close()
    _save_credentials_file(new_password)
    _log_audit(user_id, "Password Changed", "User changed own password")
    return True


def create_api_key(user_id: int, name: str) -> str:
    api_key = f"pymon_{secrets.token_urlsafe(32)}"
    key_hash = hash_password(api_key)

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO api_keys (user_id, key_hash, name, created_at) VALUES (?, ?, ?, ?)",
        (user_id, key_hash, name, datetime.now(timezone.utc).isoformat()),
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


def update_user(user_id: int, is_admin: Optional[bool] = None, must_change_password: Optional[bool] = None) -> bool:
    conn = get_db()
    c = conn.cursor()
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
    if user_id == 1:
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    _log_audit(user_id, "User Deleted", f"Deleted user id={user_id}")
    return bool(deleted)
