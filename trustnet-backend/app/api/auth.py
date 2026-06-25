"""
Auth Router
POST /api/v1/auth/register - User registration
POST /api/v1/auth/token - JWT login
POST /api/v1/auth/refresh - Refresh token
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
import jwt
from jwt.exceptions import PyJWTError, InvalidTokenError, ExpiredSignatureError
import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.postgres import User

router = APIRouter()

# Import settings
from config import settings


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User registration",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash phone if provided
    phone_hash = None
    if body.phone:
        import hashlib
        phone_hash = hashlib.sha256(body.phone.encode()).hexdigest()

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        phone_hash=phone_hash,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_token({"sub": str(user.id), "email": user.email, "type": "access"})
    refresh_token = create_token(
        {"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
    )


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="JWT login",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login and get JWT tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_token({"sub": str(user.id), "email": user.email, "type": "access"})
    refresh_token = create_token(
        {"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
    )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(refresh_token: str) -> TokenResponse:
    """Refresh access token using refresh token."""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        access_token = create_token({"sub": user_id, "type": "access"})
        new_refresh = create_token(
            {"sub": user_id, "type": "refresh"},
            expires_delta=timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS),
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        )
    except (PyJWTError, InvalidTokenError, ExpiredSignatureError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
