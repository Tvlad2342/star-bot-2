"""
Модели данных (классы для удобной работы)
"""

from dataclasses import dataclass
from typing import Optional
from utils.constants import ROLES, ROLE_EMOJIS


@dataclass
class User:
    """Модель пользователя"""
    id: int
    username: str
    stars: int
    role: int
    nickname: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя (ник или юзернейм)"""
        return self.nickname or f"@{self.username}"
    
    @property
    def role_name(self) -> str:
        """Название роли"""
        return ROLES.get(self.role, f"Уровень {self.role}")
    
    @property
    def role_emoji(self) -> str:
        """Эмодзи роли"""
        return ROLE_EMOJIS.get(self.role, "👤")
    
    def has_permission(self, required_role: int) -> bool:
        """Проверяет, достаточно ли прав"""
        return self.role >= required_role


@dataclass
class Task:
    """Модель задачи"""
    id: int
    task_number: int
    description: str
    created_by: int
    created_at: str
    deadline: str
    status: str
    completed_by: Optional[int]
    completed_at: Optional[str]
    creator_name: Optional[str] = None
    completer_name: Optional[str] = None
    
    @property
    def status_display(self) -> str:
        """Отображение статуса"""
        from utils.constants import TASK_STATUS
        return TASK_STATUS.get(self.status, self.status)
    
    @property
    def time_left(self) -> str:
        """Оставшееся время"""
        from utils.helpers import time_remaining
        return time_remaining(self.deadline)


@dataclass
class Report:
    """Модель отчета"""
    id: int
    report_date: str
    zam_id: int
    invites_count: int
    username: Optional[str] = None
    nickname: Optional[str] = None
    zam_level: Optional[int] = None