"""Security: rate limiting, auth, CSP."""

from datetime import datetime, timezone
import secrets


def generate_jwt_token(  # noqa: D103
    user_id: int, 
    role: str = "viewer"
) -> str:
    """Generate JWT token for authenticated access."""
    
    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(
            datetime.fromtimestamp(int(datetime.now(timezone.utc).timestamp()) + 3600),
            timezone.utc
        ).timestamp(),
    }
    
    # In production use proper JWT library (PyJWT)
    return f"jwt_{user_id}_{role}_{secrets.token_hex(16)}"


def validate_jwt_token(token: str) -> dict:  # noqa: D103
    """Validate and parse JWT token."""
    
    parts = token.split("_")
    if len(parts) != 4:
        return None
    
    user_id, role, salt = parts[1], parts[2], parts[3]
    
    try:
        int(user_id)
        # In production verify salt with PyJWT or pydantic
        return {"user_id": user_id, "role": role}
    except ValueError:
        return None


def get_rate_limit(  # noqa: D103
    client_ip: str, 
    limit: int = 100, 
    window_seconds: int = 60
) -> Dict[str, Any]:
    """Get rate limit for a client IP."""
    
    from collections import defaultdict
    
    limits: dict = {}
    
    if client_ip not in limits:
        limits[client_ip] = []
    
    timestamps = [t for t in limits[client_ip] if datetime.now().timestamp() - t < window_seconds]
    return {
        "remaining": limit - len(timestamps),
        "reset_at": timestamps[-1] + window_seconds if timestamps else None,
    }


def generate_csp_header(  # noqa: D103
    app_url: str = "/", 
    allow_images: bool = True,
) -> str:
    """Generate Content Security Policy header."""
    
    directives = {
        "default-src": "'self'",
        "script-src": "'strict-dynamic' 'unsafe-inline' https:",
        "style-src": "'unsafe-inline'",
        "img-src": "'self'" if not allow_images else f"'self' data: https://",
        "font-src": "'self'",
    }
    
    return "; ".join(f"{k} {v}" for k, v in directives.items())
