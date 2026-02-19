"""JWT Authentication module for PyMon"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

import bcrypt
import jwt
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
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
    admin_password: str = "admin"


auth_config = AuthConfig()


def get_db():
    import sqlite3
    # Ensure directory exists
    db_dir = os.path.dirname(auth_config.db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return sqlite3.connect(auth_config.db_path)


def init_auth_tables():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0,
        must_change_password BOOLEAN DEFAULT 1,
        created_at TEXT,
        last_login TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        key_hash TEXT NOT NULL,
        name TEXT,
        created_at TEXT,
        last_used TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    c.execute("SELECT id FROM users WHERE username = ?", (auth_config.admin_username,))
    if not c.fetchone():
        password_hash = hash_password(auth_config.admin_password)
        c.execute(
            "INSERT INTO users (username, password_hash, is_admin, must_change_password, created_at) VALUES (?, ?, 1, 1, ?)",
            (auth_config.admin_username, password_hash, datetime.utcnow().isoformat())
        )
        print(f"Created default user: {auth_config.admin_username} / {auth_config.admin_password}")
    
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, username: str, is_admin: bool, must_change: bool) -> str:
    payload = {
        "sub": username,
        "user_id": user_id,
        "is_admin": is_admin,
        "must_change_password": must_change,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> User:
    if not credentials:
        api_key = request.headers.get("X-API-Key") if request else None
        if api_key:
            return await validate_api_key(api_key)
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(credentials.credentials)
    
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
        must_change_password=bool(row["must_change_password"])
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
            c.execute("UPDATE api_keys SET last_used = ? WHERE user_id = ?", (datetime.utcnow().isoformat(), row["user_id"]))
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
            (username, password_hash, int(is_admin), datetime.utcnow().isoformat())
        )
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        return User(id=user_id, username=username, is_admin=is_admin, must_change_password=True)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")


def authenticate_user(username: str, password: str) -> Token:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, is_admin, must_change_password FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    
    if not row or not verify_password(password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    c.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.utcnow().isoformat(), row["id"]))
    conn.commit()
    conn.close()
    
    user = User(
        id=row["id"],
        username=row["username"],
        is_admin=bool(row["is_admin"]),
        must_change_password=bool(row["must_change_password"])
    )
    
    token = create_token(user.id, user.username, user.is_admin, user.must_change_password)
    return Token(access_token=token, user=user)


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    
    if not row or not verify_password(current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if len(new_password) < 6:
        conn.close()
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    new_hash = hash_password(new_password)
    c.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True


def create_api_key(user_id: int, name: str) -> str:
    api_key = f"pymon_{secrets.token_urlsafe(32)}"
    key_hash = hash_password(api_key)
    
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO api_keys (user_id, key_hash, name, created_at) VALUES (?, ?, ?, ?)",
        (user_id, key_hash, name, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    
    return api_key


def list_api_keys(user_id: int) -> list[dict]:
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, name, created_at, last_used FROM api_keys WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r["id"], "name": r["name"], "created_at": r["created_at"], "last_used": r["last_used"]} for r in rows]


def delete_api_key(user_id: int, key_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


import sqlite3
