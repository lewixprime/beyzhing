import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from webapp.routes import auth, api

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI(
    title="StarHold WebApp",
    description="WebApp для авторизации и управления подарками/звёздами",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статики и шаблонов
webapp_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(webapp_dir, "static")
templates_dir = os.path.join(webapp_dir, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Подключение роутеров
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(api.router, prefix="/api", tags=["API"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница (редирект на /webapp)"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/webapp", response_class=HTMLResponse)
async def webapp_page(request: Request, hash: str = None, type: str = None):
    """
    Главная страница WebApp
    
    Args:
        hash: Хеш фейка (опционально)
        type: Тип фейка - check/gift (опционально)
    """
    context = {
        "request": request,
        "webapp_url": Config.WEBAPP_URL,
        "bot_username": Config.BOT_USERNAME,
        "fake_hash": hash,
        "fake_type": type
    }
    
    return templates.TemplateResponse("index.html", context)

@app.get("/health")
async def health_check():
    """Health check для мониторинга"""
    return JSONResponse({
        "status": "ok",
        "service": "StarHold WebApp",
        "version": "1.0.0"
    })

@app.exception_handler(404)
async def not_found(request: Request, exc):
    """Обработка 404"""
    return JSONResponse(
        status_code=404,
        content={"error": "Not found"}
    )

@app.exception_handler(500)
async def server_error(request: Request, exc):
    """Обработка 500"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
