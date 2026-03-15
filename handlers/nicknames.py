"""
Команды для работы с никами: /addnick, /removenick, /nicklist, /setnick
"""

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from database.models import User
from database.db import set_nickname, get_nickname, delete_nickname, get_all_nicknames
from database.db import get_user_by_username
from services.permissions import check_permission
from utils.constants import STYLES, DIVIDER
from utils.helpers import escape_username
from utils.logger import send_admin_log

router = Router()


@router.message(Command("addnick"))
async def addnick_cmd(msg: Message, user: User, bot: Bot):
    """Установить себе ник"""
    if not check_permission(user, 'addnick'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply(
            f"{STYLES['info']} <b>УСТАНОВКА НИКА</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /addnick [Ваш ник]\n\n"
            f"<b>Пример:</b> /addnick Иван Иванов",
            parse_mode="HTML"
        )
        return
    
    nickname = parts[1].strip()
    
    if len(nickname) > 32:
        await msg.reply(f"{STYLES['error']} Слишком длинный ник (максимум 32 символа)", parse_mode="HTML")
        return
    
    if len(nickname) < 2:
        await msg.reply(f"{STYLES['error']} Слишком короткий ник (минимум 2 символа)", parse_mode="HTML")
        return
    
    await set_nickname(user.id, nickname)
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "📝 Новый ник": nickname
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Установка ника",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>НИК УСТАНОВЛЕН</b>\n{DIVIDER}\n\n"
        f"<b>Ваш ник:</b> {nickname}",
        parse_mode="HTML"
    )


@router.message(Command("removenick"))
async def removenick_cmd(msg: Message, user: User, bot: Bot):
    """Удалить свой ник"""
    if not check_permission(user, 'removenick_self'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    current = await get_nickname(user.id)
    if not current:
        await msg.reply(f"{STYLES['error']} У вас нет ника для удаления", parse_mode="HTML")
        return
    
    await delete_nickname(user.id)
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "🗑 Удален ник": current
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Удаление ника",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>НИК УДАЛЕН</b>\n{DIVIDER}\n\n"
        f"Ваш ник успешно удален",
        parse_mode="HTML"
    )


@router.message(Command("setnick"))
async def setnick_cmd(msg: Message, user: User, bot: Bot):
    """Установить ник другому пользователю"""
    if not check_permission(user, 'setnick'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.reply(
            f"{STYLES['info']} <b>УСТАНОВКА ЧУЖОГО НИКА</b>\n{DIVIDER}\n\n"
            f"<b>Использование:</b> /setnick @username [ник]\n\n"
            f"<b>Пример:</b> /setnick @ivan Петр Петров",
            parse_mode="HTML"
        )
        return
    
    username = parts[1].replace("@", "")
    nickname = parts[2].strip()
    
    target = await get_user_by_username(username)
    if not target:
        await msg.reply(f"{STYLES['error']} Пользователь не найден", parse_mode="HTML")
        return
    
    await set_nickname(target.id, nickname)
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "👤 Пользователь": target.display_name,
        "📝 Новый ник": nickname
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Установка ника для пользователя",
        additional_info=additional_info
    )
    
    await msg.reply(
        f"{STYLES['success']} <b>НИК УСТАНОВЛЕН</b>\n{DIVIDER}\n\n"
        f"<b>Пользователь:</b> {target.display_name}\n"
        f"<b>Новый ник:</b> {nickname}",
        parse_mode="HTML"
    )


@router.message(Command("nicklist"))
async def nicklist_cmd(msg: Message, user: User):
    """Список всех ников"""
    if not check_permission(user, 'nicklist'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав. Требуется уровень 4+", parse_mode="HTML")
        return
    
    nicknames = await get_all_nicknames()
    
    if not nicknames:
        await msg.reply(
            f"{STYLES['info']} <b>СПИСОК НИКОВ</b>\n{DIVIDER}\n\n"
            f"Еще никто не установил себе ник",
            parse_mode="HTML"
        )
        return
    
    text = f"{STYLES['list']} <b>СПИСОК ВСЕХ НИКОВ</b>\n{DIVIDER}\n\n"
    
    for i, (_, username, nickname) in enumerate(nicknames, 1):
        text += f"{i}. <b>{nickname}</b> ({escape_username(username)})\n"
    
    text += f"\n{DIVIDER}\n{STYLES['info']} Всего ников: {len(nicknames)}"
    
    await msg.reply(text, parse_mode="HTML")