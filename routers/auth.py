from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas import UserCreate, UserOut
from models import User
from auth import get_password_hash, authenticate_user, create_access_token
from database import SessionLocal

router = APIRouter(prefix="/auth", tags=["Аутентификация"])

@router.post("/register", response_model=UserOut, summary="Регистрация пользователя")
async def register(user: UserCreate, db: AsyncSession = Depends(SessionLocal)):
    existing = await db.execute(select(User).where(User.username == user.username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    hashed = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/token", summary="Получить JWT-токен")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  
    db: AsyncSession = Depends(SessionLocal)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}