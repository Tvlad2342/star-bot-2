"""
Админские команды: /users, /setnorm, /setsalary, /makezam, /history, /setot, /otinfo
"""

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from database.models import User
from database.db import (
    get_all_users, delete_user, update_user_role,
    update_report_norm, update_report_bonus, set_zam_salary,
    get_user_by_username, get_user_history, get_all_history,
    get_report_settings, get_all_zam_salaries
)
from services.permissions import check_permission, can_edit_user
from services.formatter import format_date, format_number
from utils.constants import STYLES, DIVIDER, ROLES, ROLE_EMOJIS
from utils.helpers import split_message
from utils.logger import send_admin_log
from typing import List

router = Router()


@router.message(Command("users"))
async def users_cmd(msg: Message, user: User, bot: Bot):
    """Список всех пользователей"""
    if not check_permission(user, 'users'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    users = await get_all_users()
    
    if not users:
        await msg.reply(
            f"{STYLES['info']} <b>ПОЛЬЗОВАТЕЛИ</b>\n{DIVIDER}\n\n"
            f"Пользователей пока нет",
            parse_mode="HTML"
        )
        return
    
    by_role = {}
    for u in users:
        if u.role not in by_role:
            by_role[u.role] = []
        by_role[u.role].append(u)
    
    text = f"{STYLES['user']} <b>ВСЕ ПОЛЬЗОВАТЕЛИ</b>\n{DIVIDER}\n\n"
    
    for role in sorted(by_role.keys(), reverse=True):
        role_name = ROLES.get(role, "Неизвестно")
        role_emoji = ROLE_EMOJIS.get(role, "👤")
        role_users = by_role[role]
        
        text += f"{role_emoji} <b>{role_name}</b> ({len(role_users)})\n"
        
        sorted_users = sorted(role_users, key=lambda x: x.stars, reverse=True)
        
        for i, u in enumerate(sorted_users, 1):
            stars_display = f"{STYLES['star']} {u.stars}" if u.stars > 0 else ""
            text += f"   {i}. <b>{u.display_name}</b> {stars_display}\n"
        text += "\n"
    
    text += f"{DIVIDER}\n"
    text += f"{STYLES['user']} <b>Всего пользователей:</b> {len(users)}\n"
    
    if len(text) > 4000:
        parts = split_message(text)
        for part in parts:
            await msg.reply(part, parse_mode="HTML")
    else:
        await msg.reply(text, parse_mode="HTML")


@router.message(Command("setnorm"))
async def setnorm_cmd(msg: Message, user: User, bot: Bot):
    """Установить норму инвайтов"""
    if not check_permission(user, 'setnorm'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply(
            f"{STYLES['info']} <b>УСТАНОВКА НОРМЫ</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /setnorm кол-во\n\n"
            f"<b>Пример:</b> /setnorm 5",
            parse_mode="HTML"
        )
        return
    
    try:
        norm = int(parts[1])
        if norm < 1:
            await msg.reply(f"{STYLES['error']} Норма должна быть больше 0", parse_mode="HTML")
            return
        
        await update_report_norm(norm)
        
        # Отправляем лог в админ чат в новом формате
        additional_info = {
            "📊 Новая норма": f"{norm} инвайтов"
        }
        await send_admin_log(
            bot=bot,
            user=user,
            action="Изменение нормы отчетов",
            additional_info=additional_info
        )
        
        await msg.reply(
            f"{STYLES['success']} <b>НОРМА УСТАНОВЛЕНА</b>\n{DIVIDER}\n\n"
            f"<b>Новая норма:</b> {norm} инвайтов",
            parse_mode="HTML"
        )
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Неверный формат числа", parse_mode="HTML")


@router.message(Command("setbonus"))
async def setbonus_cmd(msg: Message, user: User, bot: Bot):
    """Установить процент надбавки"""
    if not check_permission(user, 'setbonus'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply(
            f"{STYLES['info']} <b>УСТАНОВКА БОНУСА</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /setbonus %\n\n"
            f"<b>Пример:</b> /setbonus 50",
            parse_mode="HTML"
        )
        return
    
    try:
        bonus = int(parts[1])
        if bonus < 0 or bonus > 1000:
            await msg.reply(f"{STYLES['error']} Бонус должен быть от 0 до 1000%", parse_mode="HTML")
            return
        
        await update_report_bonus(bonus)
        
        # Отправляем лог в админ чат в новом формате
        additional_info = {
            "💰 Новый бонус": f"{bonus}%"
        }
        await send_admin_log(
            bot=bot,
            user=user,
            action="Изменение бонуса отчетов",
            additional_info=additional_info
        )
        
        await msg.reply(
            f"{STYLES['success']} <b>БОНУС УСТАНОВЛЕН</b>\n{DIVIDER}\n\n"
            f"<b>Новая надбавка:</b> {bonus}%",
            parse_mode="HTML"
        )
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Неверный формат числа", parse_mode="HTML")


@router.message(Command("setsalary"))
async def setsalary_cmd(msg: Message, user: User, bot: Bot):
    """Установить зарплату для уровня"""
    if not check_permission(user, 'setsalary'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            f"{STYLES['info']} <b>УСТАНОВКА ЗАРПЛАТЫ</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /setsalary уровень кол-во\n\n"
            f"<b>Пример:</b> /setsalary 1 300000",
            parse_mode="HTML"
        )
        return
    
    try:
        level = int(parts[1])
        salary = int(parts[2])
        
        if level < 1 or level > 5:
            await msg.reply(f"{STYLES['error']} Уровень должен быть от 1 до 5", parse_mode="HTML")
            return
        
        if salary < 0:
            await msg.reply(f"{STYLES['error']} Зарплата должна быть положительной", parse_mode="HTML")
            return
        
        await set_zam_salary(level, salary)
        
        role_name = ROLES.get(level, f"Уровень {level}")
        
        # Отправляем лог в админ чат в новом формате
        additional_info = {
            "👤 Уровень": role_name,
            "💵 Новая зарплата": format_number(salary)
        }
        await send_admin_log(
            bot=bot,
            user=user,
            action="Изменение зарплаты",
            additional_info=additional_info
        )
        
        await msg.reply(
            f"{STYLES['success']} <b>ЗАРПЛАТА УСТАНОВЛЕНА</b>\n{DIVIDER}\n\n"
            f"<b>{role_name}:</b> {format_number(salary)} (за 1 человека)",
            parse_mode="HTML"
        )
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Неверный формат числа", parse_mode="HTML")


@router.message(Command("makezam"))
async def makezam_cmd(msg: Message, user: User, bot: Bot):
    """Назначить заместителя"""
    if not check_permission(user, 'makezam'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) != 3:
        await msg.reply(
            f"{STYLES['info']} <b>НАЗНАЧЕНИЕ РОЛИ</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /makezam @username уровень\n\n"
            f"<b>Пример:</b> /makezam @username 3\n"
            f"<b>Пример:</b> /makezam @username 6 (только для основателя)",
            parse_mode="HTML"
        )
        return
    
    try:
        username = parts[1].replace("@", "")
        level = int(parts[2])
        
        if level < 1 or level > 6:
            await msg.reply(f"{STYLES['error']} Уровень должен быть от 1 до 6", parse_mode="HTML")
            return
        
        if level == 6 and user.role != 6:
            await msg.reply(f"{STYLES['error']} Только основатель может назначить другого основателя", parse_mode="HTML")
            return
        
        target = await get_user_by_username(username)
        if not target:
            await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
            return
        
        old_role = target.role
        await update_user_role(target.id, level)
        
        role_name = ROLES.get(level, f"Уровень {level}")
        old_role_name = ROLES.get(old_role, f"Уровень {old_role}")
        
        # Отправляем лог в админ чат в новом формате
        additional_info = {
            "👤 Пользователь": target.display_name,
            "📊 Была роль": old_role_name,
            "📊 Стала роль": role_name
        }
        await send_admin_log(
            bot=bot,
            user=user,
            action="Назначение роли",
            additional_info=additional_info
        )
        
        await msg.reply(
            f"{STYLES['success']} <b>РОЛЬ НАЗНАЧЕНА</b>\n{DIVIDER}\n\n"
            f"<b>Пользователь:</b> {target.display_name}\n"
            f"{ROLE_EMOJIS.get(level, '👤')} <b>Новая роль:</b> {role_name}",
            parse_mode="HTML"
        )
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} Уровень должен быть числом", parse_mode="HTML")


@router.message(Command("removezam"))
async def removezam_cmd(msg: Message, user: User, bot: Bot):
    """Снять заместителя"""
    if not check_permission(user, 'removezam'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) != 2:
        await msg.reply(
            f"{STYLES['info']} <b>СНЯТИЕ ЗАМЕСТИТЕЛЯ</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /removezam @username",
            parse_mode="HTML"
        )
        return
    
    username = parts[1].replace("@", "")
    target = await get_user_by_username(username)
    
    if not target:
        await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
        return
    
    old_role = target.role
    await update_user_role(target.id, 0)
    
    old_role_name = ROLES.get(old_role, f"Уровень {old_role}")
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "👤 Пользователь": target.display_name,
        "📊 Была роль": old_role_name,
        "📊 Стала роль": "Пользователь"
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Снятие роли",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>РОЛЬ СНЯТА</b>\n{DIVIDER}\n\n"
        f"<b>Пользователь:</b> {target.display_name}\n"
        f"👤 <b>Новая роль:</b> Пользователь",
        parse_mode="HTML"
    )


@router.message(Command("history"))
async def history_cmd(msg: Message, user: User):
    """История изменений пользователя"""
    if not check_permission(user, 'history'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) != 2:
        await msg.reply(
            f"{STYLES['info']} <b>ИСТОРИЯ ИЗМЕНЕНИЙ</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /history @username",
            parse_mode="HTML"
        )
        return
    
    username = parts[1].replace("@", "")
    target = await get_user_by_username(username)
    
    if not target:
        await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
        return
    
    history = await get_user_history(target.id, 20)
    
    if not history:
        await msg.reply(
            f"{STYLES['info']} <b>ИСТОРИЯ {target.display_name}</b>\n{DIVIDER}\n\n"
            f"Нет истории изменений",
            parse_mode="HTML"
        )
        return
    
    text = f"{STYLES['history']} <b>ИСТОРИЯ {target.display_name}</b>\n{DIVIDER}\n\n"
    
    for i, (issuer_id, issuer_name, amount, action, timestamp) in enumerate(history, 1):
        action_emoji = "🟢" if action == "add" else "🔴" if action == "remove" else "🟡"
        action_text = "Добавлено" if action == "add" else "Убрано" if action == "remove" else "Установлено"
        
        issuer_display = f"@{issuer_name}" if issuer_name else f"id{issuer_id}"
        date_str = format_date(timestamp)
        
        text += f"{i}. {action_emoji} <b>{action_text} {abs(amount)}</b> {STYLES['star']}\n"
        text += f"   👤 <b>Кем:</b> {issuer_display}\n"
        text += f"   {STYLES['time']} <b>Когда:</b> {date_str}\n\n"
    
    await msg.reply(text, parse_mode="HTML")


@router.message(Command("historyall"))
async def historyall_cmd(msg: Message, user: User):
    """Вся история изменений"""
    if not check_permission(user, 'historyall'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    history = await get_all_history(30)
    
    if not history:
        await msg.reply(
            f"{STYLES['info']} <b>ВСЯ ИСТОРИЯ</b>\n{DIVIDER}\n\n"
            f"Нет истории изменений",
            parse_mode="HTML"
        )
        return
    
    text = f"{STYLES['history']} <b>ВСЯ ИСТОРИЯ ИЗМЕНЕНИЙ</b>\n{DIVIDER}\n\n"
    
    for i, (issuer_id, issuer_name, target_id, target_name, amount, action, timestamp) in enumerate(history[:20], 1):
        action_emoji = "🟢" if action == "add" else "🔴" if action == "remove" else "🟡"
        action_text = "Добавлено" if action == "add" else "Убрано" if action == "remove" else "Установлено"
        
        issuer_display = f"@{issuer_name}" if issuer_name else f"id{issuer_id}"
        target_display = f"@{target_name}" if target_name else f"id{target_id}"
        date_str = format_date(timestamp)
        
        text += f"{i}. {action_emoji} <b>{action_text} {abs(amount)}</b> {STYLES['star']}\n"
        text += f"   👤 <b>Кому:</b> {target_display}\n"
        text += f"   👤 <b>Кем:</b> {issuer_display}\n"
        text += f"   {STYLES['time']} <b>Когда:</b> {date_str}\n\n"
    
    await msg.reply(text, parse_mode="HTML")


@router.message(Command("removeuser"))
async def removeuser_cmd(msg: Message, user: User, bot: Bot):
    """Удалить пользователя"""
    if not check_permission(user, 'removeuser'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) != 2:
        await msg.reply(
            f"{STYLES['info']} <b>УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /removeuser @username",
            parse_mode="HTML"
        )
        return
    
    username = parts[1].replace("@", "")
    target = await get_user_by_username(username)
    
    if not target:
        await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
        return
    
    can, reason = can_edit_user(user, target)
    if not can:
        await msg.reply(f"{STYLES['error']} {reason}", parse_mode="HTML")
        return
    
    await delete_user(target.id)
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "👤 Пользователь": target.display_name,
        "🆔 ID": str(target.id)
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Удаление пользователя",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>ПОЛЬЗОВАТЕЛЬ УДАЛЕН</b>\n{DIVIDER}\n\n"
        f"Пользователь {target.display_name} удален из БД",
        parse_mode="HTML"
    )


@router.message(Command("adduser"))
async def adduser_cmd(msg: Message, user: User, bot: Bot):
    """Добавить пользователя вручную"""
    if not check_permission(user, 'adduser'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            f"{STYLES['info']} <b>ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /adduser @username ID\n\n"
            f"<b>Пример:</b> /adduser @ivan 123456789",
            parse_mode="HTML"
        )
        return
    
    try:
        username = parts[1].replace("@", "")
        user_id = int(parts[2])
        
        from database.db import get_or_create_user
        new_user = await get_or_create_user(user_id, username)
        
        # Отправляем лог в админ чат в новом формате
        additional_info = {
            "👤 Пользователь": f"@{username}",
            "🆔 ID": str(user_id)
        }
        await send_admin_log(
            bot=bot,
            user=user,
            action="Добавление пользователя",
            additional_info=additional_info
        )
        
        await msg.reply(
            f"{STYLES['success']} <b>ПОЛЬЗОВАТЕЛЬ ДОБАВЛЕН</b>\n{DIVIDER}\n\n"
            f"<b>Юзернейм:</b> @{username}\n"
            f"<b>ID:</b> {user_id}",
            parse_mode="HTML"
        )
        
    except ValueError:
        await msg.reply(f"{STYLES['error']} ID должен быть числом", parse_mode="HTML")
    except Exception as e:
        await msg.reply(f"{STYLES['error']} Ошибка: {e}", parse_mode="HTML")


@router.message(Command("topclear"))
async def topclear_cmd(msg: Message, user: User, bot: Bot):
    """Очистить данные для топа"""
    if not check_permission(user, 'topclear'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    from database.db import clear_top_data
    count = await clear_top_data()
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "🔄 Создано снимков": str(count)
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Очистка данных топа",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>ДАННЫЕ ТОПА ОЧИЩЕНЫ</b>\n{DIVIDER}\n\n"
        f"Созданы новые снимки для {count} пользователей",
        parse_mode="HTML"
    )


@router.message(Command("refresh_top"))
async def refresh_top_cmd(msg: Message, user: User, bot: Bot):
    """Принудительное обновление снимков для топа"""
    if not check_permission(user, 'topclear'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    from database.db import clear_top_data
    count = await clear_top_data()
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "🔄 Обновлено снимков": str(count)
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Обновление снимков топа",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>СНИМКИ ОБНОВЛЕНЫ</b>\n{DIVIDER}\n\n"
        f"Созданы новые снимки для {count} пользователей",
        parse_mode="HTML"
    )


@router.message(Command("setot"))
async def setot_cmd(msg: Message, user: User):
    """Меню настройки отчетов"""
    if not check_permission(user, 'setot'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    text = (
        f"{STYLES['settings']} <b>НАСТРОЙКА ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
        f"<b>Основные настройки:</b>\n"
        f"• <code>/setnorm [кол-во]</code> — установить норму инвайтов\n"
        f"• <code>/setbonus [%]</code> — процент надбавки за превышение (0-1000%)\n\n"
        f"<b>Зарплаты по уровням:</b>\n"
        f"• <code>/setsalary 1 [сумма]</code> — зарплата для уровня 1\n"
        f"• <code>/setsalary 2 [сумма]</code> — зарплата для уровня 2\n"
        f"• <code>/setsalary 3 [сумма]</code> — зарплата для уровня 3\n"
        f"• <code>/setsalary 4 [сумма]</code> — зарплата для уровня 4\n"
        f"• <code>/setsalary 5 [сумма]</code> — зарплата для уровня 5\n\n"
        f"<b>Просмотр:</b>\n"
        f"• <code>/otinfo</code> — текущие настройки\n"
        f"{DIVIDER}"
    )
    
    await msg.reply(text, parse_mode="HTML")


@router.message(Command("otinfo"))
async def otinfo_cmd(msg: Message, user: User):
    """Информация о текущих настройках отчетов"""
    if not check_permission(user, 'otinfo'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    norm, bonus, _ = await get_report_settings()
    salaries = await get_all_zam_salaries()
    
    text = (
        f"{STYLES['settings']} <b>ТЕКУЩИЕ НАСТРОЙКИ ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
        f"<b>Норма инвайтов:</b> {norm}\n"
        f"<b>Процент надбавки:</b> {bonus}%\n\n"
        f"<b>Зарплаты по уровням:</b>\n"
    )
    
    for level in range(1, 6):
        salary = salaries.get(level, {1: 300000, 2: 400000, 3: 500000, 4: 600000, 5: 700000}.get(level))
        role_name = ROLES.get(level, f"Уровень {level}")
        text += f"• {role_name}: {format_number(salary)}\n"
    
    text += f"\n{DIVIDER}"
    
    await msg.reply(text, parse_mode="HTML")