"""
Команды для работы с задачами
"""

import asyncio
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
from database.models import User
from database.db import (
    create_task, get_all_active_tasks, get_task_by_number,
    complete_task, delete_task, check_overdue_tasks, update_overdue_status,
    get_user_by_id
)
from services.permissions import check_permission
from services.formatter import format_time_remaining, format_date
from utils.constants import STYLES, DIVIDER, TASK_STATUS
from config import TASKS_CHAT_ID, ADMIN_CHAT_ID, OVERDUE_CHECK_INTERVAL, UPCOMING_CHECK_INTERVAL
from utils.helpers import split_message
from utils.logger import logger, send_admin_log

router = Router()


# Функция отправки уведомления в чат задач
async def send_to_tasks_chat(bot: Bot, text: str):
    """Отправляет сообщение в чат задач"""
    if not TASKS_CHAT_ID or TASKS_CHAT_ID == "0":
        return False
    
    try:
        await bot.send_message(
            chat_id=TASKS_CHAT_ID,
            text=text,
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки в чат задач: {e}")
        return False


@router.message(Command("addtask"))
async def addtask_cmd(msg: Message, user: User, bot: Bot):
    """Добавить новую задачу"""
    if not check_permission(user, 'addtask'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав. Требуется уровень 3+", parse_mode="HTML")
        return
    
    parts = msg.text.split(maxsplit=3)
    if len(parts) < 4:
        await msg.reply(
            f"{STYLES['info']} <b>ДОБАВЛЕНИЕ ЗАДАЧИ</b>\n{DIVIDER}\n\n"
            f"<b>Формат:</b> /addtask [номер] [часы] [задача]\n\n"
            f"<b>Пример:</b> /addtask 1 2 Выдать ранг",
            parse_mode="HTML"
        )
        return
    
    try:
        task_number = int(parts[1])
        hours = int(parts[2])
        description = parts[3].strip()
        
        if hours < 1 or hours > 24:
            await msg.reply(f"{STYLES['error']} Часы должны быть от 1 до 24", parse_mode="HTML")
            return
        
        if task_number < 1 or task_number > 999:
            await msg.reply(f"{STYLES['error']} Номер задачи должен быть от 1 до 999", parse_mode="HTML")
            return
        
        existing = await get_task_by_number(task_number)
        if existing:
            await msg.reply(f"{STYLES['error']} Задача с номером {task_number} уже существует", parse_mode="HTML")
            return
        
        deadline = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        await create_task(task_number, description, user.id, deadline)
        
        # Логируем
        logger.task(user.id, user.username, "создал", f"задачу #{task_number}")
        
        # Отправляем лог в админ чат в новом формате
        task_info = f"#{task_number}: {description}"
        await send_admin_log(
            bot=bot,
            user=user,
            action=f"Добавление задачи #{task_number}",
            task=task_info,
            deadline=f"{hours}ч"
        )
        
        # Отправляем уведомление в чат задач
        if TASKS_CHAT_ID and TASKS_CHAT_ID != "0":
            text = (
                f"{STYLES['task']} <b>НОВАЯ ЗАДАЧА!</b>\n{DIVIDER}\n\n"
                f"<b>Задача #{task_number}:</b> {description}\n"
                f"👤 <b>Создал:</b> {user.display_name}\n"
                f"{STYLES['time']} <b>Срок:</b> {hours}ч\n{DIVIDER}"
            )
            await send_to_tasks_chat(bot, text)
        
        await msg.reply(
            f"{STYLES['success']} <b>ЗАДАЧА ДОБАВЛЕНА</b>\n{DIVIDER}\n\n"
            f"<b>Задача #{task_number}:</b> {description}\n"
            f"{STYLES['time']} <b>Срок:</b> {hours}ч",
            parse_mode="HTML"
        )
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Номер задачи и часы должны быть числами", parse_mode="HTML")
    except Exception as e:
        logger.error("Ошибка при создании задачи", user.id, user.username, e)
        await msg.reply(f"{STYLES['error']} Ошибка при создании задачи", parse_mode="HTML")


@router.message(Command("tasklist"))
async def tasklist_cmd(msg: Message, user: User):
    """Список активных задач"""
    if not check_permission(user, 'tasklist'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    await update_overdue_status()
    tasks = await get_all_active_tasks()
    
    if not tasks:
        await msg.reply(
            f"{STYLES['info']} <b>СПИСОК ЗАДАЧ</b>\n{DIVIDER}\n\n"
            f"Нет активных задач",
            parse_mode="HTML"
        )
        return
    
    text = f"{STYLES['task']} <b>АКТИВНЫЕ ЗАДАЧИ</b>\n{DIVIDER}\n\n"
    
    for task in tasks:
        creator = await get_user_by_id(task.created_by)
        creator_name = creator.display_name if creator else f"id{task.created_by}"
        
        status_emoji = "⏳" if task.status == 'pending' else "✅" if task.status == 'completed' else "⚠️"
        time_left = format_time_remaining(task.deadline)
        
        text += f"<b>#{task.task_number}. {task.description}</b>\n"
        text += f"   👤 <b>Создал:</b> {creator_name}\n"
        text += f"   {time_left}\n"
        text += f"   {status_emoji} <b>Статус:</b> {TASK_STATUS.get(task.status, task.status)}\n\n"
    
    for part in split_message(text):
        await msg.reply(part, parse_mode="HTML")


@router.message(Command("taskcomplete"))
async def taskcomplete_cmd(msg: Message, user: User, bot: Bot):
    """Отметить задачу выполненной"""
    if not check_permission(user, 'taskcomplete'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) != 2:
        await msg.reply(
            f"{STYLES['info']} Использование: /taskcomplete [номер]", 
            parse_mode="HTML"
        )
        return
    
    try:
        task_number = int(parts[1])
        task = await get_task_by_number(task_number)
        
        if not task:
            await msg.reply(f"{STYLES['error']} Задача #{task_number} не найдена", parse_mode="HTML")
            return
        
        await complete_task(task_number, user.id)
        
        # Логируем
        logger.task(user.id, user.username, "выполнил", f"задачу #{task_number}")
        
        # Отправляем лог в админ чат в новом формате
        task_info = f"#{task_number}: {task.description}"
        await send_admin_log(
            bot=bot,
            user=user,
            action=f"Выполнение задачи #{task_number}",
            task=task_info
        )
        
        # Отправляем уведомление в чат задач
        if TASKS_CHAT_ID and TASKS_CHAT_ID != "0":
            text = (
                f"{STYLES['success']} <b>ЗАДАЧА ВЫПОЛНЕНА!</b>\n{DIVIDER}\n\n"
                f"<b>Задача #{task_number}:</b> {task.description}\n"
                f"👤 <b>Выполнил:</b> {user.display_name}\n{DIVIDER}"
            )
            await send_to_tasks_chat(bot, text)
        
        await msg.reply(f"{STYLES['success']} Задача #{task_number} выполнена!", parse_mode="HTML")
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Номер задачи должен быть числом", parse_mode="HTML")
    except Exception as e:
        logger.error("Ошибка при выполнении задачи", user.id, user.username, e)
        await msg.reply(f"{STYLES['error']} Ошибка при выполнении задачи", parse_mode="HTML")


@router.message(Command("removetask"))
async def removetask_cmd(msg: Message, user: User, bot: Bot):
    """Удалить задачу"""
    if not check_permission(user, 'removetask'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав. Требуется уровень 5+", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) != 2:
        await msg.reply(
            f"{STYLES['info']} Использование: /removetask [номер]",
            parse_mode="HTML"
        )
        return
    
    try:
        task_number = int(parts[1])
        task = await get_task_by_number(task_number)
        
        if not task:
            await msg.reply(f"{STYLES['error']} Задача #{task_number} не найдена", parse_mode="HTML")
            return
        
        await delete_task(task_number, user.id)
        
        # Логируем
        logger.task(user.id, user.username, "удалил", f"задачу #{task_number}")
        
        # Отправляем лог в админ чат в новом формате
        task_info = f"#{task_number}: {task.description}"
        await send_admin_log(
            bot=bot,
            user=user,
            action=f"Удаление задачи #{task_number}",
            task=task_info
        )
        
        # Отправляем уведомление в чат задач
        if TASKS_CHAT_ID and TASKS_CHAT_ID != "0":
            text = (
                f"{STYLES['remove']} <b>ЗАДАЧА УДАЛЕНА</b>\n{DIVIDER}\n\n"
                f"<b>Задача #{task_number}:</b> {task.description}\n"
                f"👤 <b>Удалил:</b> {user.display_name}\n{DIVIDER}"
            )
            await send_to_tasks_chat(bot, text)
        
        await msg.reply(f"{STYLES['success']} Задача #{task_number} удалена", parse_mode="HTML")
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Номер задачи должен быть числом", parse_mode="HTML")
    except Exception as e:
        logger.error("Ошибка при удалении задачи", user.id, user.username, e)
        await msg.reply(f"{STYLES['error']} Ошибка при удалении задачи", parse_mode="HTML")


# ========== ФОНОВЫЕ ЗАДАЧИ ==========

async def check_overdue_notifications(bot: Bot):
    """Проверяет просроченные задачи"""
    logger.system("🔄 Запуск проверки просроченных задач")
    
    while True:
        try:
            overdue = await check_overdue_tasks()
            
            for task in overdue:
                creator = await get_user_by_id(task.created_by)
                creator_name = creator.display_name if creator else f"id{task.created_by}"
                
                if TASKS_CHAT_ID and TASKS_CHAT_ID != "0":
                    text = (
                        f"{STYLES['warning']} <b>⚠️ ЗАДАЧА ПРОСРОЧЕНА!</b>\n{DIVIDER}\n\n"
                        f"<b>Задача #{task.task_number}:</b> {task.description}\n"
                        f"👤 <b>Создал:</b> {creator_name}\n"
                        f"{STYLES['time']} <b>Дедлайн был:</b> {task.deadline}\n{DIVIDER}"
                    )
                    await send_to_tasks_chat(bot, text)
            
            await update_overdue_status()
            await asyncio.sleep(OVERDUE_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Ошибка в check_overdue_notifications: {e}")
            await asyncio.sleep(60)


async def check_upcoming_tasks(bot: Bot):
    """Проверяет задачи, до которых осталось меньше часа"""
    logger.system("🔄 Запуск проверки приближающихся задач")
    
    while True:
        try:
            tasks = await get_all_active_tasks()
            now = datetime.now()
            
            for task in tasks:
                try:
                    deadline = datetime.strptime(task.deadline, "%Y-%m-%d %H:%M:%S")
                    time_left = deadline - now
                    
                    if timedelta(minutes=30) <= time_left <= timedelta(hours=1):
                        if TASKS_CHAT_ID and TASKS_CHAT_ID != "0":
                            text = (
                                f"{STYLES['warning']} <b>⚠️ ЗАДАЧА СКОРО ПРОСРОЧИТСЯ!</b>\n{DIVIDER}\n\n"
                                f"<b>Задача #{task.task_number}:</b> {task.description}\n"
                                f"{STYLES['time']} <b>Осталось:</b> {format_time_remaining(task.deadline)}\n{DIVIDER}"
                            )
                            await send_to_tasks_chat(bot, text)
                except Exception as e:
                    continue
            
            await asyncio.sleep(UPCOMING_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Ошибка в check_upcoming_tasks: {e}")
            await asyncio.sleep(60)