"""
Команды для работы со звездами: /addstar, /removestar, /setstars, /stats, /top
"""

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from database.models import User
from database.db import (
    update_user_stars, add_history, create_star_snapshot,
    get_user_by_username, update_user_role, get_user_growth,
    get_top_overall, get_top_by_period, get_nickname
)
from services.permissions import check_permission, role_by_stars
from services.formatter import create_progress_bar
from utils.constants import STYLES, DIVIDER, ROLES, ROLE_EMOJIS
from utils.helpers import escape_username
from utils.logger import send_admin_log
from datetime import datetime, timedelta

router = Router()


@router.message(Command("stats"))
async def stats_cmd(msg: Message, user: User):
    """Просмотр статистики"""
    parts = msg.text.split()

    if len(parts) == 1:
        if not check_permission(user, 'stats'):
            await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
            return
        
        week_growth = await get_user_growth(user.id, 7)
        month_growth = await get_user_growth(user.id, 30)
        
        current_stars = user.stars
        next_level = user.role + 1
        progress_text = ""
        
        if next_level <= 5:
            next_level_stars = {
                1: 10, 2: 20, 3: 40, 4: 80, 5: 200
            }.get(next_level, 0)
            
            if next_level_stars > 0:
                progress = create_progress_bar(current_stars, next_level_stars)
                percent = int((current_stars / next_level_stars) * 100)
                progress_text = f"\n\n📊 <b>Прогресс до {ROLES[next_level]}:</b>\n{progress} {percent}%"
        
        text = (
            f"{user.role_emoji} <b>СТАТИСТИКА {user.display_name}</b>\n{DIVIDER}\n\n"
            f"{STYLES['star']} <b>Звезды:</b> {user.stars}\n"
            f"{user.role_emoji} <b>Роль:</b> {user.role_name}\n"
            f"📈 <b>Рост за неделю:</b> +{week_growth} ⭐️\n"
            f"📊 <b>Рост за месяц:</b> +{month_growth} ⭐️"
            f"{progress_text}"
        )
        
        await msg.reply(text, parse_mode="HTML")
    
    elif len(parts) == 2:
        if not check_permission(user, 'stats_with_user'):
            await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
            return

        username = parts[1].replace("@", "")
        target = await get_user_by_username(username)
        
        if not target:
            await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
            return
        
        week_growth = await get_user_growth(target.id, 7)
        month_growth = await get_user_growth(target.id, 30)
        
        text = (
            f"{target.role_emoji} <b>СТАТИСТИКА {target.display_name}</b>\n{DIVIDER}\n\n"
            f"{STYLES['star']} <b>Звезды:</b> {target.stars}\n"
            f"{target.role_emoji} <b>Роль:</b> {target.role_name}\n"
            f"📈 <b>Рост за неделю:</b> +{week_growth} ⭐️\n"
            f"📊 <b>Рост за месяц:</b> +{month_growth} ⭐️"
        )
        
        await msg.reply(text, parse_mode="HTML")


async def handle_star_change(msg: Message, user: User, action: str):
    """Общая логика для изменения звезд"""
    parts = msg.text.split()
    
    if len(parts) != 3:
        action_names = {"add": "ДОБАВЛЕНИЕ", "remove": "УДАЛЕНИЕ", "set": "УСТАНОВКА"}
        await msg.reply(
            f"{STYLES['info']} <b>{action_names[action]} ЗВЕЗД</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /{action}star количество @username\n\n"
            f"<b>Пример:</b> /{action}star 5 @username",
            parse_mode="HTML"
        )
        return None, None, None
    
    try:
        amount = int(parts[1])
        if amount < 0:
            await msg.reply(f"{STYLES['error']} Количество не может быть отрицательным", parse_mode="HTML")
            return None, None, None
        
        username = parts[2].replace("@", "")
        target = await get_user_by_username(username)
        
        if not target:
            await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
            return None, None, None
        
        return amount, target, username
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Количество должно быть числом", parse_mode="HTML")
        return None, None, None


@router.message(Command("addstar"))
async def addstar_cmd(msg: Message, user: User, bot: Bot):
    """Добавить звезды"""
    if not check_permission(user, 'addstar'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    result = await handle_star_change(msg, user, "add")
    if not result[0]:
        return
    
    amount, target, username = result
    
    if target.role == 6 and user.role != 6:
        await msg.reply(f"{STYLES['error']} Нельзя изменять звезды основателя", parse_mode="HTML")
        return
    
    old_stars = target.stars
    new_stars = target.stars + amount
    
    await update_user_stars(target.id, new_stars)
    await add_history(user.id, target.id, amount, "add")
    await create_star_snapshot(target.id, new_stars)
    
    if target.role != 6:
        new_role = role_by_stars(new_stars)
        if new_role != target.role:
            await update_user_role(target.id, new_role)
    
    # Отправляем лог в админ чат
    additional_info = {
        "👤 Пользователь": target.display_name,
        "⭐ Было": str(old_stars),
        "⭐ Стало": str(new_stars),
        "➕ Добавлено": f"+{amount}"
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Добавление звезд",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>ЗВЕЗДЫ ДОБАВЛЕНЫ</b>\n{DIVIDER}\n\n"
        f"<b>Пользователь:</b> {target.display_name}\n"
        f"{STYLES['add']} <b>Добавлено:</b> +{amount}\n"
        f"{STYLES['star']} <b>Было:</b> {old_stars}\n"
        f"{STYLES['star']} <b>Стало:</b> {new_stars}",
        parse_mode="HTML"
    )


@router.message(Command("removestar"))
async def removestar_cmd(msg: Message, user: User, bot: Bot):
    """Убрать звезды"""
    if not check_permission(user, 'removestar'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    result = await handle_star_change(msg, user, "remove")
    if not result[0]:
        return
    
    amount, target, username = result
    
    if target.role == 6 and user.role != 6:
        await msg.reply(f"{STYLES['error']} Нельзя изменять звезды основателя", parse_mode="HTML")
        return
    
    old_stars = target.stars
    new_stars = max(0, target.stars - amount)
    
    await update_user_stars(target.id, new_stars)
    await add_history(user.id, target.id, -amount, "remove")
    await create_star_snapshot(target.id, new_stars)
    
    if target.role != 6:
        new_role = role_by_stars(new_stars)
        if new_role != target.role:
            await update_user_role(target.id, new_role)
    
    # Отправляем лог в админ чат
    additional_info = {
        "👤 Пользователь": target.display_name,
        "⭐ Было": str(old_stars),
        "⭐ Стало": str(new_stars),
        "➖ Убрано": f"-{amount}"
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Удаление звезд",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>ЗВЕЗДЫ УБРАНЫ</b>\n{DIVIDER}\n\n"
        f"<b>Пользователь:</b> {target.display_name}\n"
        f"{STYLES['remove']} <b>Убрано:</b> -{amount}\n"
        f"{STYLES['star']} <b>Было:</b> {old_stars}\n"
        f"{STYLES['star']} <b>Стало:</b> {new_stars}",
        parse_mode="HTML"
    )


@router.message(Command("setstars"))
async def setstars_cmd(msg: Message, user: User, bot: Bot):
    """Установить звезды"""
    if not check_permission(user, 'setstars'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) != 3:
        await msg.reply(
            f"{STYLES['info']} <b>УСТАНОВКА ЗВЕЗД</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /setstars количество @username\n\n"
            f"<b>Пример:</b> /setstars 50 @username",
            parse_mode="HTML"
        )
        return
    
    try:
        amount = int(parts[1])
        if amount < 0:
            await msg.reply(f"{STYLES['error']} Количество не может быть отрицательным", parse_mode="HTML")
            return
        
        username = parts[2].replace("@", "")
        target = await get_user_by_username(username)
        
        if not target:
            await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
            return
        
        if target.role == 6 and user.role != 6:
            await msg.reply(f"{STYLES['error']} Нельзя изменять звезды основателя", parse_mode="HTML")
            return
        
        old_stars = target.stars
        new_stars = amount
        
        await update_user_stars(target.id, new_stars)
        await add_history(user.id, target.id, new_stars, "set")
        await create_star_snapshot(target.id, new_stars)
        
        if target.role != 6:
            new_role = role_by_stars(new_stars)
            if new_role != target.role:
                await update_user_role(target.id, new_role)
        
        # Отправляем лог в админ чат
        additional_info = {
            "👤 Пользователь": target.display_name,
            "⭐ Было": str(old_stars),
            "⭐ Стало": str(new_stars),
            "⚙ Установлено": str(amount)
        }
        await send_admin_log(
            bot=bot,
            user=user,
            action="Установка звезд",
            additional_info=additional_info
        )
        
        await msg.reply(
            f"{STYLES['success']} <b>ЗВЕЗДЫ УСТАНОВЛЕНЫ</b>\n{DIVIDER}\n\n"
            f"<b>Пользователь:</b> {target.display_name}\n"
            f"{STYLES['star']} <b>Было:</b> {old_stars}\n"
            f"{STYLES['star']} <b>Стало:</b> {new_stars}",
            parse_mode="HTML"
        )
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Количество должно быть числом", parse_mode="HTML")
    except Exception as e:
        await msg.reply(f"{STYLES['error']} Ошибка: {e}", parse_mode="HTML")


@router.message(Command("top"))
async def top_cmd(msg: Message, user: User):
    """Топ пользователей"""
    if not check_permission(user, 'top'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    
    if len(parts) == 1:
        # Общий топ
        users = await get_top_overall(10)
        
        if not users:
            await msg.reply(f"{STYLES['info']} Пользователей пока нет", parse_mode="HTML")
            return
        
        text = f"{STYLES['top']} <b>ОБЩИЙ ТОП ПО ЗВЕЗДАМ</b>\n{DIVIDER}\n\n"
        
        for i, (user_id, username, stars, role) in enumerate(users, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            role_emoji = ROLE_EMOJIS.get(role, "👤")
            
            nickname = await get_nickname(user_id)
            name = nickname if nickname else f"@{username}"
            
            text += f"{medal} <b>{name}</b> {role_emoji}\n   {stars} {STYLES['star']}\n\n"
        
        await msg.reply(text, parse_mode="HTML")
    
    elif len(parts) >= 2:
        # Топ за период
        period = parts[1].lower()
        
        # Определяем тип периода
        if period in ["день", "day", "1"]:
            days = 1
            period_type = 'days'
            period_text = "ДЕНЬ"
            users = await get_top_by_period(days, 10, period_type)
            
        elif period in ["неделя", "week", "7"]:
            period_type = 'week'
            period_text = "НЕДЕЛЮ"
            users = await get_top_by_period(7, 10, period_type)
            
        elif period in ["месяц", "month", "30"]:
            period_type = 'month'
            period_text = "МЕСЯЦ"
            users = await get_top_by_period(30, 10, period_type)
            
        else:
            await msg.reply(
                f"{STYLES['info']} <b>ТОП ЗА ПЕРИОД</b>\n{DIVIDER}\n\n"
                f"Используй: день, неделя или месяц\n"
                f"Пример: /top день",
                parse_mode="HTML"
            )
            return
        
        if not users:
            await msg.reply(f"{STYLES['info']} Нет данных за {period}", parse_mode="HTML")
            return
        
        # Получаем период текста из первого элемента (все элементы имеют одинаковый period_text)
        date_range = users[0][6] if len(users[0]) > 6 else ""
        
        if period_type == 'week':
            text = f"{STYLES['top']} <b>ТОП ЗА {period_text} ({date_range})</b>\n{DIVIDER}\n\n"
        elif period_type == 'month':
            text = f"{STYLES['top']} <b>ТОП ЗА {period_text} {date_range}</b>\n{DIVIDER}\n\n"
        else:
            text = f"{STYLES['top']} <b>ТОП ЗА {period_text}</b>\n{DIVIDER}\n\n"
        
        for i, user_data in enumerate(users, 1):
            user_id, username, current, old, growth, role, _ = user_data
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            
            nickname = await get_nickname(user_id)
            name = nickname if nickname else f"@{username}"
            
            text += f"{medal} <b>{name}</b>\n"
            text += f"   📈 +{growth} {STYLES['star']} (всего: {current})\n\n"
        
        await msg.reply(text, parse_mode="HTML")