from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re

class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Имя пользователя: 3-20 символов, буквы, цифры и подчеркивания"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль: минимум 8 символов"
    )

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'[0-9]', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v

class UserOut(BaseModel):
    id: int
    username: str

    model_config = {
        "from_attributes": True
    }

class FlashcardCreate(BaseModel):
    foreign_word: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Иностранное слово или фраза"
    )
    native_word: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Перевод на родной язык"
    )
    example: Optional[str] = Field(
        None,
        max_length=500,
        description="Пример использования в предложении"
    )

class FlashcardUpdate(BaseModel):
    foreign_word: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )
    native_word: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )
    example: Optional[str] = Field(
        None,
        max_length=500
    )

class FlashcardOut(BaseModel):
    id: int
    foreign_word: str
    native_word: str
    example: Optional[str] = None

    model_config = {
        "from_attributes": True
    }