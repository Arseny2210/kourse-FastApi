from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Base, engine, SessionLocal
from models import User, Flashcard
from auth import get_current_user, authenticate_user, create_access_token, get_password_hash
import os
from jose import jwt
from datetime import datetime, timedelta
from admin import setup_admin  
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

os.makedirs("templates", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

templates = Jinja2Templates(directory="templates")

app = FastAPI(
    title="Словарь иностранных слов",
    description="API для карточек, тестов и отслеживания прогресса изучения",
    version="0.1.0",
    servers=[{"url": "http://127.0.0.1:8000", "description": "Local server"}],
    openapi_tags=[
        {"name": "🔐 Аутентификация", "description": "Регистрация, вход и выход из системы."},
        {"name": "📚 Карточки", "description": "Управление карточками: создание, редактирование, удаление, изменение статуса и просмотр."},
    ],
    swagger_ui_init_oauth={
        "clientId": "swagger-ui",
        "appName": "Dictionary API",
        "scopes": []
    },
    swagger_ui_parameters={"persistAuthorization": True}
)

admin = setup_admin(app)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="🏠 Главная страница",
    description="Перенаправляет пользователя на страницу входа или регистрации."
)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def get_current_user_from_cookie(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не авторизован",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise credentials_exception

    if access_token.startswith("Bearer "):
        token = access_token[7:]
    else:
        token = access_token
    
    try:
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # Получаем пользователя из базы
        async with SessionLocal() as db:
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalars().first()
            if user is None:
                raise credentials_exception
            return user
    except Exception as e:
        print(f"Ошибка аутентификации из куки: {str(e)}")
        raise credentials_exception

# Защищённая страница дашборда
@app.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="📊 Личный кабинет",
    description="""
    👋 Показывает все карточки текущего пользователя.  
    📈 Отображает статистику: всего карточек, выучено, в процессе.  
    🔒 Доступен только авторизованным пользователям (через куки с JWT).
    """,
    tags=["📚 Карточки"]
)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie)
):
    async with SessionLocal() as db:
        result = await db.execute(
            select(Flashcard).where(Flashcard.owner_id == current_user.id)
        )
        flashcards = result.scalars().all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "flashcards": flashcards
    })

@app.post(
    "/web/login",
    response_class=HTMLResponse,
    summary="🔑 Вход в систему",
    description="""
    📥 Принимает имя пользователя и пароль через HTML-форму.  
    ✅ При успешной аутентификации устанавливает JWT-токен в куки и перенаправляет в личный кабинет.  
    ❌ При ошибке показывает сообщение на той же странице.
    """, tags=["🔐 Аутентификация"]
)
async def web_login(request: Request):
    """Обработка HTML формы входа"""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    if not username or not password:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "login_error": "Имя пользователя и пароль обязательны"
        }, status_code=400)
    
    async with SessionLocal() as db:
        user = await authenticate_user(db, username, password)
        if not user:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "login_error": "Неверное имя пользователя или пароль"
            }, status_code=401)
        
        access_token = create_access_token({"sub": user.username})
        

        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token", 
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=1800, 
            secure=False,  
            samesite="lax"
        )
        return response


@app.post(
    "/web/flashcards",
    response_class=HTMLResponse,
    summary="➕ Добавить новую карточку",
    description="""
    💡 Добавляет карточку иностранного слова в коллекцию пользователя.  
    🌍 Требуется: **иностранное слово** и **перевод**.  
    📖 Пример использования — опционален (до 500 символов).  
    ✅ Карточка сразу появится в личном кабинете.
    """,
    tags=["📚 Карточки"]
)
async def create_flashcard_web(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie)
):
    form = await request.form()
    foreign_word = form.get("foreign_word")
    native_word = form.get("native_word")
    example = form.get("example", "")
    
    if not foreign_word or not native_word:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "flashcards": [],
            "error": "Иностранное слово и перевод обязательны"
        }, status_code=400)
    
    if len(foreign_word) > 100 or len(native_word) > 100:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "flashcards": [],
            "error": "Слова не должны превышать 100 символов"
        }, status_code=400)
    
    if example and len(example) > 500:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "flashcards": [],
            "error": "Пример не должен превышать 500 символов"
        }, status_code=400)
    
    async with SessionLocal() as db:
        try:
            new_flashcard = Flashcard(
                foreign_word=foreign_word,
                native_word=native_word,
                example=example if example else None,
                owner_id=current_user.id
            )
            db.add(new_flashcard)
            await db.commit()
            await db.refresh(new_flashcard)
            
            result = await db.execute(
                select(Flashcard).where(Flashcard.owner_id == current_user.id)
            )
            flashcards = result.scalars().all()
            
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "user": current_user,
                "flashcards": flashcards,
                "success": "Карточка успешно добавлена!"
            })
            
        except Exception as e:
            print(f"Ошибка создания карточки: {str(e)}")
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "user": current_user,
                "flashcards": [],
                "error": "Ошибка при создании карточки. Попробуйте позже."
            }, status_code=500)

@app.post(
    "/web/register",
    response_class=HTMLResponse,
    summary="🆕 Регистрация нового пользователя",
    description="""
    📝 Создаёт нового пользователя по данным из формы.  
    🔒 Пароль хешируется (макс. 72 байта для совместимости с bcrypt).  
    🚫 Имя должно быть от 3 до 20 символов, пароль — минимум 8 символов.  
    ✅ После регистрации можно сразу войти.
    """,
    tags=["🔐 Аутентификация"]
)
async def web_register(request: Request):
    """Обработка HTML формы регистрации"""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    if not username or not password:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "register_error": "Имя пользователя и пароль обязательны"
        }, status_code=400)
    
    if len(username) < 3 or len(username) > 20:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "register_error": "Имя пользователя должно быть от 3 до 20 символов"
        }, status_code=400)
    
    if len(password) < 8:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "register_error": "Пароль должен быть не менее 8 символов"
        }, status_code=400)
    
    if len(password.encode('utf-8')) > 72:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "register_error": "Пароль слишком длинный (максимум 72 байта). Пожалуйста, сократите его."
        }, status_code=400)
    
    async with SessionLocal() as db:
        try:
            existing = await db.execute(select(User).where(User.username == username))
            if existing.scalars().first():
                return templates.TemplateResponse("index.html", {
                    "request": request,
                    "register_error": "Имя пользователя уже занято"
                }, status_code=400)
            
            hashed_password = get_password_hash(password)
            db_user = User(username=username, hashed_password=hashed_password)
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            
            return templates.TemplateResponse("index.html", {
                "request": request,
                "success_message": "Регистрация успешна! Теперь вы можете войти."
            })
        except Exception as e:
            print(f"Ошибка регистрации: {str(e)}")
            return templates.TemplateResponse("index.html", {
                "request": request,
                "register_error": "Ошибка при регистрации. Попробуйте позже."
            }, status_code=500)

@app.get(
    "/web/flashcards/{card_id}/edit",
    response_class=HTMLResponse,
    summary="✏️ Открыть редактирование карточки",
    description="""
    🖊️ Отображает форму для изменения карточки.  
    🔍 Проверяет, что карточка принадлежит текущему пользователю.  
    🛑 Если карточка не найдена — возвращает 404.
    """,
    tags=["📚 Карточки"]
)
async def edit_flashcard_form(
    request: Request,
    card_id: int,
    current_user: User = Depends(get_current_user_from_cookie)
):
    async with SessionLocal() as db:
        result = await db.execute(
            select(Flashcard).where(
                Flashcard.id == card_id,
                Flashcard.owner_id == current_user.id
            )
        )
        flashcard = result.scalars().first()
        
        if not flashcard:
            raise HTTPException(status_code=404, detail="Карточка не найдена")
        
        return templates.TemplateResponse("edit_flashcard.html", {
            "request": request,
            "user": current_user,
            "flashcard": flashcard
        })

@app.post(
    "/web/flashcards/{card_id}/update",
    response_class=HTMLResponse,
    summary="💾 Сохранить изменения в карточке",
    description="""
    🔄 Обновляет текст карточки: слово, перевод и пример.  
    🔐 Доступно только владельцу.  
    ✅ После сохранения возвращает в личный кабинет с подтверждением.
    """,tags=["📚 Карточки"]
)
async def update_flashcard_web(
    request: Request,
    card_id: int,
    current_user: User = Depends(get_current_user_from_cookie)
):
    form = await request.form()
    foreign_word = form.get("foreign_word")
    native_word = form.get("native_word")
    example = form.get("example", "")
    
    if not foreign_word or not native_word:
        return templates.TemplateResponse("edit_flashcard.html", {
            "request": request,
            "user": current_user,
            "flashcard": {"id": card_id},
            "error": "Иностранное слово и перевод обязательны"
        }, status_code=400)
    
    async with SessionLocal() as db:
        result = await db.execute(
            select(Flashcard).where(
                Flashcard.id == card_id,
                Flashcard.owner_id == current_user.id
            )
        )
        flashcard = result.scalars().first()
        
        if not flashcard:
            raise HTTPException(status_code=404, detail="Карточка не найдена")
        
        flashcard.foreign_word = foreign_word
        flashcard.native_word = native_word
        flashcard.example = example if example else None
        await db.commit()
        
        result = await db.execute(
            select(Flashcard).where(Flashcard.owner_id == current_user.id)
        )
        flashcards = result.scalars().all()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "flashcards": flashcards,
            "success": "Карточка успешно обновлена!"
        })

@app.post(
    "/web/flashcards/{card_id}/mark-learned",
    response_class=HTMLResponse,
    summary="✅ Пометить карточку как выученную",
    description="""
    🔄 Переключает статус: **выучено** ↔ **не выучено**.  
    📊 Увеличивает счётчик повторений.  
    📅 Обновляет дату последнего повторения.  
    🎯 Помогает отслеживать прогресс изучения.
    """,
    tags=["📚 Карточки"]
)
async def mark_flashcard_learned(
    request: Request,
    card_id: int,
    current_user: User = Depends(get_current_user_from_cookie)
):
    async with SessionLocal() as db:
        result = await db.execute(
            select(Flashcard).where(
                Flashcard.id == card_id,
                Flashcard.owner_id == current_user.id
            )
        )
        flashcard = result.scalars().first()
        
        if not flashcard:
            raise HTTPException(status_code=404, detail="Карточка не найдена")
        
        flashcard.is_learned = not flashcard.is_learned
        flashcard.repetitions += 1
        flashcard.last_reviewed = datetime.utcnow()
        
        await db.commit()
        
        result = await db.execute(
            select(Flashcard).where(Flashcard.owner_id == current_user.id)
        )
        flashcards = result.scalars().all()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "flashcards": flashcards,
            "success": f"Карточка '{flashcard.foreign_word}' помечена как {'выученная' if flashcard.is_learned else 'не выученная'}"
        })

@app.post(
    "/web/flashcards/{card_id}/delete",
    response_class=HTMLResponse,
    summary="🗑️ Удалить карточку",
    description="""
    ❌ Полностью удаляет карточку из базы данных.  
    🔒 Доступно только владельцу.  
    ⚠️ Действие **нельзя отменить** — запрашивается подтверждение в браузере.
    """,
    tags=["📚 Карточки"]
)
async def delete_flashcard_web(
    request: Request,
    card_id: int,
    current_user: User = Depends(get_current_user_from_cookie)
):
    async with SessionLocal() as db:
        result = await db.execute(
            select(Flashcard).where(
                Flashcard.id == card_id,
                Flashcard.owner_id == current_user.id
            )
        )
        flashcard = result.scalars().first()
        
        if not flashcard:
            raise HTTPException(status_code=404, detail="Карточка не найдена")
        
        await db.delete(flashcard)
        await db.commit()
        
        result = await db.execute(
            select(Flashcard).where(Flashcard.owner_id == current_user.id)
        )
        flashcards = result.scalars().all()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "flashcards": flashcards,
            "success": f"Карточка '{flashcard.foreign_word}' успешно удалена"
        })

@app.get(
    "/logout",
    response_class=HTMLResponse,
    summary="🚪 Выход из системы",
    description="""
    🍪 Удаляет JWT-токен из куки.  
    🔄 Перенаправляет на главную страницу.  
    👋 Пользователь больше не авторизован.
    """,
    tags=["🔐 Аутентификация"]
)
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.is_superuser == True))
        superuser = result.scalars().first()
        if not superuser:
            hashed = get_password_hash("admin123")  # Пароль по умолчанию
            admin_user = User(username="admin", hashed_password=hashed, is_superuser=True)
            db.add(admin_user)
            await db.commit()
            print("✅ Создан суперпользователь для админки:")
            print("   Логин: admin")
            print("   Пароль: admin123")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Обработчик всех HTTP-ошибок, включая 404."""
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "404.html", 
            {"request": request}, 
            status_code=404
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации (422 Unprocessable Entity)"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": [
                {
                    "field": ".".join(str(loc) for loc in error["loc"][1:]),
                    "message": error["msg"],
                    "type": error["type"]
                }
                for error in exc.errors()
            ],
            "status_code": 422
        }
    )