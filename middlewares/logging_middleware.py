"""
Middleware для логирования команд
"""

import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from utils.logger import logger


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования команд"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        user = data.get('user')
        
        try:
            result = await handler(event, data)
            duration = int((time.time() - start_time) * 1000)
            
            # Логируем команды
            if isinstance(event, Message) and event.text:
                if event.text.startswith('/'):
                    user_id = user.id if user else event.from_user.id
                    username = user.username if user else event.from_user.username
                    command = event.text.split()[0]
                    
                    logger.cmd(user_id, username, command, duration)
            
            return result
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            user_id = user.id if user else getattr(event.from_user, 'id', None)
            username = user.username if user else getattr(event.from_user, 'username', None)
            
            logger.error(f"Ошибка: {e}", user_id, username)
            raise