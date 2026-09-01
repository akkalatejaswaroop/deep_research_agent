"""
Authentication and Authorization Module
"""
import time
import hashlib
import secrets
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError

import os

# JWT Configuration
def _get_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET_KEY")
    if env_secret:
        return env_secret
    secret_file = os.path.join(os.path.dirname(__file__), ".jwt_secret")
    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    new_secret = secrets.token_urlsafe(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(new_secret)
    except Exception:
        pass
    return new_secret

JWT_SECRET_KEY = _get_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting storage (in production, use Redis)
_rate_limit_storage: Dict[str, list] = {}
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX_REQUESTS = 100  # requests per window

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = time.time() + expires_delta
    else:
        expire = time.time() + (JWT_EXPIRATION_HOURS * 3600)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Get current user from JWT token."""
    if credentials is None:
        # For development, allow unauthenticated access
        # In production, this should raise an exception
        return {"user_id": "anonymous", "authenticated": False}
    
    try:
        payload = verify_token(credentials.credentials)
        return {"user_id": payload.get("sub", "unknown"), "authenticated": True}
    except HTTPException:
        # For development, allow unauthenticated access
        return {"user_id": "anonymous", "authenticated": False}


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    @staticmethod
    def is_allowed(client_id: str) -> bool:
        """Check if request is allowed based on rate limit."""
        now = time.time()
        window_start = now - _RATE_LIMIT_WINDOW
        
        # Clean old entries
        if client_id in _rate_limit_storage:
            _rate_limit_storage[client_id] = [
                timestamp for timestamp in _rate_limit_storage[client_id]
                if timestamp > window_start
            ]
        else:
            _rate_limit_storage[client_id] = []
        
        # Check if under limit
        if len(_rate_limit_storage[client_id]) >= _RATE_LIMIT_MAX_REQUESTS:
            return False
        
        # Add current request
        _rate_limit_storage[client_id].append(now)
        return True


def rate_limit_dependency(client_id: str = "default"):
    """Dependency for rate limiting."""
    if not RateLimiter.is_allowed(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )