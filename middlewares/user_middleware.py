"""
Middleware для автоматической регистрации пользователей
"""

from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from database.db import get_or_create_user, update_user_role
from database.models import User
from config import FOUNDER_IDS


class UserMiddleware(BaseMiddleware):
    """Автоматически создает пользователя и проверяет права основателя"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем или создаем пользователя
        user = await self._get_or_create_user(event)
        
        if user:
            data['user'] = user
        
        return await handler(event, data)
    
    async def _get_or_create_user(self, event: TelegramObject) -> Optional[User]:
        """Получает или создает пользователя"""
        from_user = None
        
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user
        
        if not from_user:
            return None
        
        username = from_user.username or f"id{from_user.id}"
        user = await get_or_create_user(from_user.id, username)
        
        # Проверка основателя
        if from_user.id in FOUNDER_IDS and user.role != 6:
            await update_user_role(user.id, 6)
            user.role = 6
        
        return user