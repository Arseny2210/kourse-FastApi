from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from models import User, Flashcard
from database import engine, SessionLocal
from auth import authenticate_user, create_access_token
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form["username"]
        password = form["password"]
        
        async with SessionLocal() as db:
            user = await authenticate_user(db, username, password)
            if user and user.is_superuser:
                token = create_access_token({"sub": user.username})
                request.session.update({"token": f"Bearer {token}"})
                return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        
        try:
            clean_token = token.split(" ")[1] if " " in token else token
            from auth import SECRET_KEY, ALGORITHM
            payload = jwt.decode(clean_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return False
            
            async with SessionLocal() as db:
                result = await db.execute(select(User).where(User.username == username))
                user = result.scalars().first()
                if user and user.is_superuser:
                    request.state.user = user
                    return True
            return False
        except Exception as e:
            print(f"Ошибка аутентификации админки: {str(e)}")
            return False

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.is_superuser]
    column_details_list = [User.id, User.username, User.is_superuser]
    form_excluded_columns = [User.hashed_password]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Пользователь"
    name_plural = "Пользователи"

class FlashcardAdmin(ModelView, model=Flashcard):
    column_list = [Flashcard.id, Flashcard.foreign_word, Flashcard.native_word, Flashcard.is_learned]
    column_details_list = [Flashcard.id, Flashcard.foreign_word, Flashcard.native_word, Flashcard.example, Flashcard.is_learned, Flashcard.repetitions, Flashcard.last_reviewed, Flashcard.owner]
    column_searchable_list = [Flashcard.foreign_word, Flashcard.native_word]
    can_create = True
    can_edit = True
    can_delete = True
    name = "Карточка"
    name_plural = "Карточки"

def setup_admin(app):
    authentication_backend = AdminAuth(secret_key=os.getenv("SECRET_KEY", "your-secret-key"))
    admin = Admin(app, engine, authentication_backend=authentication_backend, title="Админка Словаря")
    admin.add_view(UserAdmin)
    admin.add_view(FlashcardAdmin)
    return admin