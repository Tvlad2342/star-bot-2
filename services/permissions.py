"""
Проверка прав доступа (улучшенная версия)
"""

from typing import Optional, Dict, List, Set, Tuple
from enum import IntEnum
from database.models import User
from utils.constants import COMMAND_PERMISSIONS
import logging

logger = logging.getLogger(__name__)


class Role(IntEnum):
    """Роли пользователей"""
    USER = 0
    ZAM1 = 1
    ZAM2 = 2
    ZAM3 = 3
    ZAM4 = 4
    ZAM5 = 5
    FOUNDER = 6
    
    @property
    def name_ru(self) -> str:
        """Русское название роли"""
        names = {
            0: "Пользователь",
            1: "Зам 1 уровня",
            2: "Зам 2 уровня",
            3: "Зам 3 уровня",
            4: "Зам 4 уровня",
            5: "Зам 5 уровня",
            6: "Основатель"
        }
        return names.get(self.value, "Неизвестно")
    
    @property
    def emoji(self) -> str:
        """Эмодзи роли"""
        emojis = {
            0: "👤",
            1: "🥉",
            2: "🥈",
            3: "🥇",
            4: "💎",
            5: "👑",
            6: "⚜️"
        }
        return emojis.get(self.value, "👤")


class Permission:
    """Класс для проверки прав"""
    
    def __init__(self, required_role: int):
        self.required_role = required_role
    
    def check(self, user: User) -> bool:
        """Проверяет, есть ли права"""
        return user.role >= self.required_role
    
    def __call__(self, user: User) -> bool:
        return self.check(user)


# Кэш для прав
_permission_cache = {}
_role_cache = {}


def check_permission(user: User, command: str) -> bool:
    """Проверяет, есть ли у пользователя права на команду"""
    # Проверяем кэш
    cache_key = f"{user.id}:{command}"
    if cache_key in _permission_cache:
        return _permission_cache[cache_key]
    
    required = COMMAND_PERMISSIONS.get(command, 6)
    result = user.role >= required
    
    # Кэшируем результат на 5 минут
    _permission_cache[cache_key] = result
    
    logger.debug(f"Permission check: user={user.id} ({user.role}) "
                f"command={command} (need={required}) -> {result}")
    
    return result


def clear_permission_cache(user_id: Optional[int] = None):
    """Очищает кэш прав"""
    global _permission_cache
    
    if user_id:
        # Удаляем только для конкретного пользователя
        keys_to_delete = [k for k in _permission_cache if k.startswith(f"{user_id}:")]
        for key in keys_to_delete:
            _permission_cache.pop(key, None)
        logger.debug(f"Cleared permission cache for user {user_id}")
    else:
        _permission_cache.clear()
        logger.debug("Cleared all permission cache")


def role_by_stars(stars: int) -> int:
    """Определяет роль по количеству звезд"""
    # Проверяем кэш
    if stars in _role_cache:
        return _role_cache[stars]
    
    thresholds = [
        (200, 5),
        (80, 4),
        (40, 3),
        (20, 2),
        (10, 1)
    ]
    
    for threshold, role in thresholds:
        if stars >= threshold:
            _role_cache[stars] = role
            return role
    
    _role_cache[stars] = 0
    return 0


def can_edit_user(editor: User, target: User) -> Tuple[bool, str]:
    """Может ли редактор изменять целевого пользователя"""
    if editor.id == target.id:
        return False, "Нельзя редактировать самого себя"
    
    if editor.role == Role.FOUNDER:
        return True, ""
    
    if target.role == Role.FOUNDER:
        return False, "Нельзя редактировать основателя"
    
    if editor.role > target.role:
        return True, ""
    
    return False, f"Недостаточно прав (нужен уровень {target.role + 1}+)"


def get_users_with_permission(users: List[User], min_role: int) -> List[User]:
    """Возвращает пользователей с минимальной ролью"""
    return [u for u in users if u.role >= min_role]


def get_highest_role_user(users: List[User]) -> Optional[User]:
    """Возвращает пользователя с наивысшей ролью"""
    if not users:
        return None
    return max(users, key=lambda u: u.role)