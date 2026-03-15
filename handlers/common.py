"""
Общие команды: /start, /help
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.models import User
from services.permissions import check_permission
from utils.constants import STYLES, DIVIDER

router = Router()


@router.message(Command("start"))
async def start_cmd(msg: Message, user: User):
    """Запуск бота"""
    welcome_text = (
        f"{STYLES['info']} <b>ДОБРО ПОЖАЛОВАТЬ!</b>\n{DIVIDER}\n\n"
        f"Я - бот для управления заместителями и отслеживания статистики.\n\n"
        f"{STYLES['star']} <b>Основные возможности:</b>\n"
        f"• Учет звезд и ролей\n"
        f"• Система отчетов по инвайтам\n"
        f"• Управление задачами\n"
        f"• Топы и статистика\n\n"
        f"{STYLES['info']} Для просмотра всех команд используй /help"
    )
    await msg.reply(welcome_text, parse_mode="HTML")


@router.message(Command("help"))
async def help_cmd(msg: Message, user: User):
    """Помощь по командам"""
    if not check_permission(user, 'help'):
        await msg.reply(f"{STYLES['error']} Недостаточно прав", parse_mode="HTML")
        return
    
    help_text = f"{STYLES['info']} <b>📋 ПОМОЩЬ ПО БОТУ</b>\n{DIVIDER}\n\n"
    
    # Команды для всех (уровень 0+)
    help_text += (
        f"{STYLES['user']} <b>УРОВЕНЬ 0 (Пользователь и выше):</b>\n"
        f"• <code>/start</code> - приветствие\n"
        f"• <code>/addnick [ник]</code> - установить себе ник\n\n"
    )
    
    # Команды для уровня 1+ (ZAM 1 и выше)
    if user.role >= 1:
        help_text += (
            f"{STYLES['user']} <b>УРОВЕНЬ 1+ (ZAM 1 и выше):</b>\n"
            f"• <code>/help</code> - это меню\n"
            f"• <code>/stats</code> - ваша статистика\n"
            f"• <code>/removenick</code> - удалить свой ник\n"
            f"• <code>/tasklist</code> - список активных задач\n"
            f"• <code>/taskcomplete [номер]</code> - отметить выполнение задачи\n\n"
        )
    
    # Команды для уровня 3+ (ZAM 3 и выше)
    if user.role >= 3:
        help_text += (
            f"{STYLES['stats']} <b>УРОВЕНЬ 3+ (ZAM 3 и выше):</b>\n"
            f"• <code>/addtask [номер] [часы] [задача]</code> - добавить задачу\n\n"
        )
    
    # Команды для уровня 4+ (ZAM 4 и выше)
    if user.role >= 4:
        help_text += (
            f"{STYLES['stats']} <b>УРОВЕНЬ 4+ (ZAM 4 и выше):</b>\n"
            f"• <code>/top</code> - общий топ по звездам\n"
            f"• <code>/top день</code> - топ за день\n"
            f"• <code>/top неделя</code> - топ за неделю\n"
            f"• <code>/top месяц</code> - топ за месяц\n"
            f"• <code>/nicklist</code> - список всех ников\n\n"
        )
    
    # Команды для уровня 5+ (ZAM 5 и выше)
    if user.role >= 5:
        help_text += (
            f"{STYLES['admin']} <b>УРОВЕНЬ 5+ (ZAM 5 и выше):</b>\n"
            f"• <code>/stats @user</code> - статистика пользователя\n"
            f"• <code>/addstar N @user</code> - добавить звезды\n"
            f"• <code>/removestar N @user</code> - убрать звезды\n"
            f"• <code>/makezam @user уровень</code> - назначить зама (1-5)\n"
            f"• <code>/removezam @user</code> - снять зама\n"
            f"• <code>/removetask [номер]</code> - удалить задачу\n"
            f"• <code>/ot</code> - меню отчетов (интерактивное)\n"
            f"• <code>/otlist</code> - список всех отчетов\n"
            f"• <code>/addot @user N [дата]</code> - быстро добавить отчет\n"
            f"• <code>/ot [дата]</code> - просмотр отчета за дату\n"
            f"• <code>/removeot [дата]</code> - удалить отчет за дату\n\n"
        )
    
    # Команды для уровня 6 (Основатель)
    if user.role >= 6:
        help_text += (
            f"{STYLES['admin']} <b>УРОВЕНЬ 6 (ОСНОВАТЕЛЬ):</b>\n"
            f"• <code>/setstars N @user</code> - установить количество звезд\n"
            f"• <code>/history @user</code> - история изменений пользователя\n"
            f"• <code>/historyall</code> - история всех изменений\n"
            f"• <code>/users</code> - список всех пользователей\n"
            f"• <code>/bdusers</code> - расширенный список пользователей\n"
            f"• <code>/bdinfo</code> - информация о базе данных\n"
            f"• <code>/removeuser @user</code> - удалить пользователя\n"
            f"• <code>/adduser @user ID</code> - добавить пользователя вручную\n"
            f"• <code>/setnick @user [ник]</code> - установить ник другому\n"
            f"• <code>/removenick @user</code> - удалить чужой ник\n"
            f"• <code>/topclear</code> - очистить данные для топа\n"
            f"• <code>/refresh_top</code> - обновить снимки для топа\n"
            
            f"{STYLES['settings']} <b>НАСТРОЙКИ ОТЧЕТОВ:</b>\n"
            f"• <code>/setot</code> - меню настройки отчетов\n"
            f"• <code>/otinfo</code> - текущие настройки\n"
            f"• <code>/setnorm [кол-во]</code> - установить норму инвайтов\n"
            f"• <code>/setbonus [%]</code> - установить процент надбавки\n"
            f"• <code>/setsalary [уровень] [сумма]</code> - установить зарплату\n\n"
        )
    
    # Добавляем информацию о текущем уровне
    help_text += (
        f"{DIVIDER}\n"
        f"{STYLES['info']} <b>Ваш уровень:</b> {user.role_name} {user.role_emoji}\n"
        f"{STYLES['star']} <b>Ваши звезды:</b> {user.stars}\n"
    )
    
    await msg.reply(help_text, parse_mode="HTML")