"""
Команды для просмотра информации о базе данных и пользователях
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.models import User
from database.db import get_db, get_all_users
from services.permissions import check_permission
from utils.constants import STYLES, DIVIDER, ROLES
from utils.helpers import split_message
import os

router = Router()


@router.message(Command("bdinfo"))
async def bdinfo_cmd(msg: Message, user: User):
    """Информация о базе данных"""
    if not check_permission(user, 'bdinfo'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав. Требуется уровень 6", parse_mode="HTML")
        return
    
    # Получаем размер файла БД
    db_path = "database.db"
    db_size = 0
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path)
    
    # Получаем статистику по таблицам
    async with get_db() as db:
        # Количество пользователей
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            users_count = (await cursor.fetchone())[0]
        
        # Количество отчетов
        async with db.execute("SELECT COUNT(*) FROM reports") as cursor:
            reports_count = (await cursor.fetchone())[0]
        
        # Количество задач
        async with db.execute("SELECT COUNT(*) FROM tasks") as cursor:
            tasks_count = (await cursor.fetchone())[0]
        
        # Количество записей в истории
        async with db.execute("SELECT COUNT(*) FROM history") as cursor:
            history_count = (await cursor.fetchone())[0]
    
    # Форматируем размер
    def format_size(size):
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}ТБ"
    
    text = (
        f"ИНФОРМАЦИЯ О БАЗЕ ДАННЫХ\n{DIVIDER}\n\n"
        f"Файл: {db_path}\n"
        f"Размер: {format_size(db_size)}\n\n"
        f"Статистика таблиц:\n"
        f"  Пользователи: {users_count}\n"
        f"  Отчеты: {reports_count}\n"
        f"  Задачи: {tasks_count}\n"
        f"  История: {history_count}\n"
        f"{DIVIDER}"
    )
    
    await msg.reply(text, parse_mode="HTML")


@router.message(Command("bdusers"))
async def bdusers_cmd(msg: Message, user: User):
    """Расширенная информация о пользователях"""
    if not check_permission(user, 'bdusers'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав. Требуется уровень 6", parse_mode="HTML")
        return
    
    users = await get_all_users()
    
    if not users:
        await msg.reply(
            f"СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n{DIVIDER}\n\n"
            f"Пользователей пока нет\n{DIVIDER}",
            parse_mode="HTML"
        )
        return
    
    # Группируем по ролям для статистики
    role_stats = {}
    for u in users:
        role_stats[u.role] = role_stats.get(u.role, 0) + 1
    
    text = f"СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n{DIVIDER}\n\n"
    
    for i, u in enumerate(users, 1):
        # Формируем ник или username
        if u.nickname:
            name_display = f"{u.nickname} (@{u.username})"
        else:
            name_display = f"@{u.username}"
        
        # Роль
        role_name = ROLES.get(u.role, f"Уровень {u.role}")
        
        text += f"{i}. {name_display} | {u.stars} ⭐ | {role_name}\n"
        text += f"   ID: {u.id}\n\n"
    
    # Добавляем разделитель перед статистикой
    text += f"{DIVIDER}\n\n"
    
    # Статистика
    text += f"Всего пользователей: {len(users)}\n"
    text += f"По ролям:\n"
    for role, count in sorted(role_stats.items(), reverse=True):
        role_name = ROLES.get(role, f"Уровень {role}")
        text += f"  {role_name}: {count}\n"
    
    text += f"{DIVIDER}"
    
    # Разбиваем длинное сообщение
    for part in split_message(text):
        await msg.reply(part, parse_mode="HTML")