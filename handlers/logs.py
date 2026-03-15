"""
Команды для просмотра логов и статистики
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database.models import User
from services.permissions import check_permission
from utils.logger import logger
from utils.metrics import metrics
from utils.trace import get_trace_info, format_trace
from utils.constants import STYLES, DIVIDER
from datetime import datetime, timedelta
import json
from pathlib import Path

router = Router()


@router.message(Command("logs"))
async def logs_cmd(msg: Message, user: User):
    """Просмотр логов и статистики"""
    if not check_permission(user, 'logs'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав. Требуется уровень 5+", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    
    if len(parts) == 1:
        # Общая статистика
        await show_logs_help(msg)
    else:
        subcommand = parts[1].lower()
        
        if subcommand == "stats":
            await show_stats(msg)
        elif subcommand == "errors":
            await show_errors(msg, parts[2] if len(parts) > 2 else "10")
        elif subcommand == "today":
            await show_today_logs(msg)
        elif subcommand == "clear" and user.role == 6:
            await clear_logs(msg)
        else:
            await msg.reply(
                f"{STYLES['info']} <b>Неизвестная команда</b>\n"
                f"Используйте /logs для списка команд",
                parse_mode="HTML"
            )


async def show_logs_help(msg: Message):
    """Показывает справку по логам"""
    text = (
        f"{STYLES['stats']} <b>КОМАНДЫ ДЛЯ ПРОСМОТРА ЛОГОВ</b>\n{DIVIDER}\n\n"
        f"<b>/logs stats</b> - общая статистика\n"
        f"<b>/logs errors [N]</b> - последние N ошибок\n"
        f"<b>/logs today</b> - логи за сегодня\n"
        f"<b>/logs clear</b> - очистить старые логи (только Founder)\n"
        f"{DIVIDER}"
    )
    
    await msg.reply(text, parse_mode="HTML")


async def show_stats(msg: Message):
    """Показывает общую статистику"""
    stats = metrics.get_stats()
    
    text = (
        f"{STYLES['stats']} <b>СТАТИСТИКА БОТА</b>\n{DIVIDER}\n\n"
        f"⏱ <b>Аптайм:</b> {stats['uptime']}\n"
        f"📊 <b>Всего команд:</b> {stats['commands_total']}\n"
        f"📈 <b>Команд за час:</b> {stats['commands_today']}\n"
        f"❌ <b>Ошибок за час:</b> {stats['errors_last_hour']}\n\n"
        f"<b>🏆 ТОП КОМАНД:</b>\n"
    )
    
    for cmd, count in stats['top_commands'].items():
        text += f"   • {cmd}: {count}\n"
    
    await msg.reply(text, parse_mode="HTML")


async def show_errors(msg: Message, limit: str):
    """Показывает последние ошибки"""
    try:
        n = int(limit)
        if n > 20:
            n = 20
    except:
        n = 10
    
    # Читаем из файла логов
    log_file = Path("logs") / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    
    if not log_file.exists():
        await msg.reply(f"{STYLES['info']} Файл логов не найден", parse_mode="HTML")
        return
    
    errors = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '❌ [ERROR]' in line:
                errors.append(line.strip())
    
    if not errors:
        await msg.reply(f"{STYLES['success']} Ошибок не найдено", parse_mode="HTML")
        return
    
    text = f"{STYLES['error']} <b>ПОСЛЕДНИЕ {n} ОШИБОК</b>\n{DIVIDER}\n\n"
    
    for error in errors[-n:]:
        text += f"{error}\n\n"
    
    await msg.reply(text[:4000], parse_mode="HTML")


async def show_today_logs(msg: Message):
    """Показывает логи за сегодня"""
    log_file = Path("logs") / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    
    if not log_file.exists():
        await msg.reply(f"{STYLES['info']} Логи за сегодня не найдены", parse_mode="HTML")
        return
    
    # Читаем последние 30 строк
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()[-30:]
    
    if not lines:
        await msg.reply(f"{STYLES['info']} Логи пусты", parse_mode="HTML")
        return
    
    text = f"{STYLES['stats']} <b>ПОСЛЕДНИЕ СОБЫТИЯ</b>\n{DIVIDER}\n\n"
    text += "```\n"
    text += "".join(lines)
    text += "```"
    
    await msg.reply(text, parse_mode="HTML")


async def clear_logs(msg: Message):
    """Очищает старые логи (только Founder)"""
    log_dir = Path("logs")
    if not log_dir.exists():
        await msg.reply(f"{STYLES['info']} Папка с логами не найдена", parse_mode="HTML")
        return
    
    # Удаляем логи старше 3 дней
    cutoff = datetime.now() - timedelta(days=3)
    deleted = 0
    
    for file in log_dir.glob("*.log"):
        try:
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            if file_time < cutoff:
                file.unlink()
                deleted += 1
        except:
            continue
    
    await msg.reply(
        f"{STYLES['success']} <b>ЛОГИ ОЧИЩЕНЫ</b>\n{DIVIDER}\n\n"
        f"Удалено файлов: {deleted}",
        parse_mode="HTML"
    )