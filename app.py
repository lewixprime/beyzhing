import os
import sys
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Добавляем текущую директорию в путь Python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Пытаемся импортировать Config
try:
    from config import Config
    WEBAPP_URL = getattr(Config, 'WEBAPP_URL', 'https://example.com')
    BOT_USERNAME = getattr(Config, 'BOT_USERNAME', '@StarHoldBot')
    logger.info("Config успешно загружен")
except ImportError as e:
    logger.warning(f"Config не найден: {e}, используем переменные окружения")
    WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://example.com")
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "@StarHoldBot")

# Инициализация FastAPI
app = FastAPI(
    title="StarHold WebApp",
    description="WebApp для авторизации и управления подарками/звёздами",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ПРАВИЛЬНЫЕ пути для ПЛОСКОЙ структуры (БЕЗ webapp/)
static_dir = os.path.join(BASE_DIR, "static")        # ← УБРАЛИ webapp/
templates_dir = os.path.join(BASE_DIR, "templates")  # ← УБРАЛИ webapp/

# Создаём директории если нет
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"Static dir: {static_dir}")
logger.info(f"Templates dir: {templates_dir}")
logger.info(f"Static exists: {os.path.exists(static_dir)}")
logger.info(f"Templates exists: {os.path.exists(templates_dir)}")

# Подключение статики и шаблонов
try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    templates = Jinja2Templates(directory=templates_dir)
    logger.info("✅ Статика и шаблоны подключены успешно")
except Exception as e:
    logger.error(f"❌ Ошибка подключения статики: {e}")

# Пытаемся подключить роутеры (БЕЗ webapp.)
try:
    from routes import auth, api  # ← УБРАЛИ webapp.
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(api.router, prefix="/api", tags=["API"])
    logger.info("✅ Роутеры auth и api подключены")
except ImportError as e:
    logger.warning(f"⚠️ Роутеры не подключены: {e}")
    logger.warning("WebApp будет работать без /auth и /api эндпоинтов")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"❌ Ошибка рендера главной страницы: {e}")
        # Временный fallback HTML
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>StarHold WebApp</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5; }
                h1 { color: #FFD700; }
            </style>
        </head>
        <body>
            <h1>🌟 StarHold WebApp</h1>
            <p>Сервер работает!</p>
            <p><small>Ошибка загрузки шаблона. Проверьте файлы.</small></p>
        </body>
        </html>
        """, status_code=200)

@app.get("/webapp", response_class=HTMLResponse)
async def webapp_page(request: Request, hash: str = None, type: str = None):
    """Главная страница WebApp"""
    try:
        context = {
            "request": request,
            "webapp_url": WEBAPP_URL,
            "bot_username": BOT_USERNAME,
            "fake_hash": hash,
            "fake_type": type
        }
        return templates.TemplateResponse("index.html", context)
    except Exception as e:
        logger.error(f"❌ Ошибка рендера WebApp: {e}")
        return HTMLResponse(content=f"<h1>Ошибка WebApp</h1><p>{str(e)}</p>", status_code=500)

@app.get("/health")
async def health_check():
    """Health check"""
    index_exists = os.path.exists(os.path.join(templates_dir, "index.html"))
    css_exists = os.path.exists(os.path.join(static_dir, "css", "style.css"))
    js_exists = os.path.exists(os.path.join(static_dir, "js", "app.js"))
    
    return JSONResponse({
        "status": "ok",
        "service": "StarHold WebApp",
        "version": "1.0.0",
        "static_exists": os.path.exists(static_dir),
        "templates_exists": os.path.exists(templates_dir),
        "index_html_exists": index_exists,
        "style_css_exists": css_exists,
        "app_js_exists": js_exists,
        "base_dir": BASE_DIR
    })

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.exception_handler(500)
async def server_error(request: Request, exc):
    logger.error(f"Server error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
