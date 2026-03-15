"""
Простой логгер только для консоли и функция отправки логов в админ чат
"""

import logging
import sys
from typing import Optional
from datetime import datetime
from aiogram import Bot
from database.models import User
from config import ADMIN_CHAT_ID
from utils.constants import STYLES, DIVIDER


class ConsoleLogger:
    """Логгер только для консоли"""
    
    def __init__(self):
        self.logger = logging.getLogger("bot")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers = []
        
        # Только консоль
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
        self.logger.addHandler(console)
    
    def _user_str(self, user_id: int, username: Optional[str] = None) -> str:
        if username:
            return f"@{username} [ID:{user_id}]"
        return f"ID:{user_id}"
    
    def cmd(self, user_id: int, username: Optional[str], command: str, duration: int = 0):
        user = self._user_str(user_id, username)
        if duration:
            self.logger.info(f"📌 {user} → {command} ({duration}ms)")
        else:
            self.logger.info(f"📌 {user} → {command}")
    
    def error(self, message: str, user_id: Optional[int] = None, username: Optional[str] = None):
        if user_id:
            user = self._user_str(user_id, username)
            self.logger.error(f"❌ {user} | {message}")
        else:
            self.logger.error(f"❌ {message}")
    
    def system(self, message: str):
        self.logger.info(f"🤖 {message}")
    
    def task(self, user_id: int, username: Optional[str], action: str, task_info: str):
        user = self._user_str(user_id, username)
        self.logger.info(f"📋 {user} {action}: {task_info}")
    
    def warning(self, message: str):
        self.logger.warning(f"⚠️ {message}")


# Функция для форматирования лога в новом стиле
def format_admin_log(initiator: str, user_id: int, action: str, 
                     task: str = None, deadline: str = None, 
                     additional_info: dict = None) -> str:
    """
    Форматирует лог для отправки в админ чат в новом стиле
    """
    now = datetime.now()
    date_str = now.strftime('%d.%m.%Y')
    time_str = now.strftime('%H:%M')
    
    log_lines = [
        "📋 ЛОГ",
        "╔═════════════════════════════",
        "║",
        f"║ 👤 Инициатор: {initiator}",
        f"║ 🆔 ID: {user_id}",
        "║",
        "╟─────────────────────────────",
        "║",
        f"║ 🔹 Действие: {action}",
        "║",
    ]
    
    # Добавляем информацию о задаче если есть
    if task:
        log_lines.extend([
            "╟─────────────────────────────",
            "║",
            f"║ 📌 Задача: {task}",
        ])
        if deadline:
            log_lines.append(f"║ ⏰ Срок: {deadline}")
        log_lines.append("║")
    
    # Добавляем дополнительную информацию если есть
    if additional_info:
        log_lines.append("╟─────────────────────────────")
        log_lines.append("║")
        for key, value in additional_info.items():
            log_lines.append(f"║ {key}: {value}")
        log_lines.append("║")
    
    # Добавляем дату и время
    log_lines.extend([
        "╟─────────────────────────────",
        "║",
        f"║ 📅 Дата: {date_str} | {time_str} (мск)",
        "║",
        "╚══════════════════════════════"
    ])
    
    return "\n".join(log_lines)


# Функция для отправки структурированных логов в админ чат
async def send_admin_log(bot: Bot, user: User, action: str, 
                         task: str = None, deadline: str = None,
                         additional_info: dict = None):
    """Отправляет структурированный лог в админ чат"""
    if not ADMIN_CHAT_ID:
        return
    
    # Формируем красивое имя инициатора
    if user.nickname:
        initiator = f"{user.nickname} (@{user.username})"
    else:
        initiator = f"@{user.username}"
    
    # Форматируем лог
    log_text = format_admin_log(
        initiator=initiator,
        user_id=user.id,
        action=action,
        task=task,
        deadline=deadline,
        additional_info=additional_info
    )
    
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=log_text,
            parse_mode="HTML"
        )
    except Exception as e:
        # Не используем logger здесь чтобы избежать циклической зависимости
        print(f"Ошибка отправки лога в админ чат: {e}")


# Глобальный экземпляр логгера
logger = ConsoleLogger()