from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas import FlashcardCreate, FlashcardUpdate, FlashcardOut
from models import Flashcard
from auth import get_current_user
from database import SessionLocal

router = APIRouter(prefix="/flashcards", tags=["Карточки"])

@router.post("/", response_model=FlashcardOut, summary="Создать карточку")
async def create_flashcard(
    card: FlashcardCreate,
    db: AsyncSession = Depends(SessionLocal),
    current_user = Depends(get_current_user)
):
    db_card = Flashcard(**card.model_dump(), owner_id=current_user.id)
    db.add(db_card)
    await db.commit()
    await db.refresh(db_card)
    return db_card

@router.get("/", response_model=list[FlashcardOut], summary="Список всех карточек")
async def read_flashcards(
    db: AsyncSession = Depends(SessionLocal),
    current_user = Depends(get_current_user)
):
    result = await db.execute(select(Flashcard).where(Flashcard.owner_id == current_user.id))
    return result.scalars().all()

@router.get("/{card_id}", response_model=FlashcardOut, summary="Получить карточку по ID")
async def read_flashcard(
    card_id: int,
    db: AsyncSession = Depends(SessionLocal),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(Flashcard).where(
            Flashcard.id == card_id,
            Flashcard.owner_id == current_user.id
        )
    )
    card = result.scalars().first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    return card

@router.put("/{card_id}", response_model=FlashcardOut, summary="Обновить карточку")
async def update_flashcard(
    card_id: int,
    card_update: FlashcardUpdate,
    db: AsyncSession = Depends(SessionLocal),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(Flashcard).where(
            Flashcard.id == card_id,
            Flashcard.owner_id == current_user.id
        )
    )
    db_card = result.scalars().first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    for key, value in card_update.model_dump(exclude_unset=True).items():
        setattr(db_card, key, value)
    await db.commit()
    await db.refresh(db_card)
    return db_card

@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить карточку")
async def delete_flashcard(
    card_id: int,
    db: AsyncSession = Depends(SessionLocal),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(Flashcard).where(
            Flashcard.id == card_id,
            Flashcard.owner_id == current_user.id
        )
    )
    db_card = result.scalars().first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    await db.delete(db_card)
    await db.commit()
    return