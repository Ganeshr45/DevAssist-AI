from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.rate_limit import client_key, enforce_limit
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models.authz import Role
from app.models.telemetry import AuditLog
from app.models.user import RefreshToken, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


def require_allowed_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin or origin.rstrip("/") not in {
        item.rstrip("/") for item in settings.allowed_origins
    }:
        raise HTTPException(403, "Request origin is not allowed")


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "refresh_token",
        token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    await enforce_limit(
        f"register:{client_key(request)}",
        settings.login_attempts_per_window,
        settings.login_window_seconds,
    )
    email = str(body.email).lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(409, "An account with this email already exists")
    user = User(
        email=email,
        display_name=body.display_name.strip(),
        password_hash=hash_password(body.password),
    )
    admin_emails = {
        item.strip().lower() for item in settings.admin_emails.split(",") if item.strip()
    }
    role_name = "admin" if email in admin_emails else "member"
    role = await db.scalar(select(Role).where(Role.name == role_name))
    if not role:
        raise HTTPException(503, "Role data is missing; run database migrations")
    user.roles.append(role)
    db.add(user)
    try:
        await db.flush()
        db.add(AuditLog(actor_user_id=user.id, event_name="account.registered", safe_metadata={}))
        raw_refresh = new_refresh_token()
        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            )
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "An account with this email already exists") from None
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(
        access_token=create_access_token(str(user.id)), user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    await enforce_limit(
        f"login:{client_key(request)}",
        settings.login_attempts_per_window,
        settings.login_window_seconds,
    )
    user = await db.scalar(
        select(User).options(selectinload(User.roles)).where(User.email == str(body.email).lower())
    )
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        db.add(AuditLog(event_name="auth.login_failed", safe_metadata={}))
        await db.commit()
        raise HTTPException(401, "Email or password is incorrect")
    raw_refresh = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.add(AuditLog(actor_user_id=user.id, event_name="auth.login", safe_metadata={}))
    await db.commit()
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(
        access_token=create_access_token(str(user.id)), user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    require_allowed_origin(request)
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(401, "Refresh credential missing")
    stored = await db.scalar(
        select(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_token(raw_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        .with_for_update()
    )
    if not stored:
        raise HTTPException(401, "Refresh credential is invalid or expired")
    user = await db.scalar(
        select(User).options(selectinload(User.roles)).where(User.id == stored.user_id)
    )
    if not user or not user.is_active:
        raise HTTPException(401, "Account is unavailable")
    stored.revoked_at = datetime.now(UTC)
    next_token = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(next_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    await db.commit()
    set_refresh_cookie(response, next_token)
    return TokenResponse(
        access_token=create_access_token(str(user.id)), user=UserResponse.model_validate(user)
    )


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    require_allowed_origin(request)
    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        token = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))
        )
        if token and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
            await db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")
