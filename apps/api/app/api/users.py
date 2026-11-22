from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.users import ProfileUpdate

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=UserResponse)
async def me(user: User = Depends(current_user)):
    return user


@router.patch("/users/me", response_model=UserResponse)
async def update_me(
    body: ProfileUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    if body.display_name is not None:
        user.display_name = body.display_name.strip()
    if body.email is not None:
        user.email = str(body.email).lower()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "That email address is already in use") from None
    await db.refresh(user)
    return user
