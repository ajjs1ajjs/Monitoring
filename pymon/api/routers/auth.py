import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from pymon.auth import (
    APIKeyCreate,
    PasswordChange,
    Token,
    User,
    UserLogin,
    authenticate_user,
    change_password,
    create_api_key,
    get_admin_user,
    get_current_user,
    list_api_keys,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_limiter = Limiter(key_func=get_remote_address)


class AdminUserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class AdminUserUpdate(BaseModel):
    password: str | None = None
    is_admin: bool | None = None
    must_change_password: bool | None = None

@router.post("/login", response_model=Token)
@_limiter.limit("10/minute")
async def login(request: Request, data: UserLogin):
    # bcrypt verification is blocking (~100-300ms); keep it off the event loop.
    return await asyncio.to_thread(authenticate_user, data.username, data.password)

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/change-password")
async def change_pwd(data: PasswordChange, current_user: User = Depends(get_current_user)):
    change_password(current_user.id, data.current_password, data.new_password)
    return {"status": "ok"}

@router.post("/api-keys")
async def create_key(data: APIKeyCreate, current_user: User = Depends(get_current_user)):
    key = create_api_key(current_user.id, data.name)
    return {"api_key": key, "name": data.name}

@router.get("/api-keys")
async def list_keys(current_user: User = Depends(get_current_user)):
    return {"api_keys": list_api_keys(current_user.id)}

@router.get("/users")
async def list_users(current_user: User = Depends(get_admin_user)):
    from pymon.auth import list_users as _list_users
    return {"users": _list_users()}

@router.post("/users")
async def create_user(data: AdminUserCreate, current_user: User = Depends(get_admin_user)):
    from pymon.auth import create_user as _create_user
    from pymon.auth import validate_password_complexity
    validate_password_complexity(data.password)
    try:
        user = _create_user(
            username=data.username,
            password=data.password,
            is_admin=data.is_admin,
        )
        return {"status": "ok", "user_id": user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{user_id}")
async def update_user(user_id: int, data: AdminUserUpdate, current_user: User = Depends(get_admin_user)):
    from pymon.auth import set_password as _set_password
    from pymon.auth import update_user as _update_user

    if data.password:
        _set_password(user_id, data.password)
        return {"status": "ok", "password_changed": True}

    if data.is_admin is not None or data.must_change_password is not None:
        _update_user(user_id, is_admin=data.is_admin, must_change_password=data.must_change_password)

    return {"status": "ok"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(get_admin_user)):
    from pymon.auth import delete_user as _delete_user
    _delete_user(user_id)
    return {"status": "ok"}
