"""
Главный файл запуска бота
"""

import asyncio
import sys
from pathlib import Path
import platform

sys.path.append(str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.exceptions import TelegramAPIError
from config import TOKEN, config
from database.db import init_db

# Импорты хендлеров
from handlers import common, nicknames, admin, stars, reports, tasks, bdinfo
from middlewares.user_middleware import UserMiddleware
from middlewares.logging_middleware import LoggingMiddleware
from utils.logger import logger
from handlers.tasks import check_overdue_notifications, check_upcoming_tasks

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== ПОДКЛЮЧЕНИЕ MIDDLEWARE ==========
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())
dp.message.middleware(UserMiddleware())
dp.callback_query.middleware(UserMiddleware())

# ========== ПОДКЛЮЧЕНИЕ РОУТЕРОВ ==========
dp.include_router(common.router)
dp.include_router(nicknames.router)
dp.include_router(admin.router)
dp.include_router(stars.router)
dp.include_router(reports.router)
dp.include_router(tasks.router)
dp.include_router(bdinfo.router)


async def set_commands():
    """Устанавливает команды бота"""
    commands = [
        # Основные команды
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="📋 Помощь"),
        BotCommand(command="stats", description="📊 Статистика"),
        
        # Ники
        BotCommand(command="addnick", description="✏️ Установить ник"),
        BotCommand(command="removenick", description="🗑 Удалить свой ник"),
        BotCommand(command="setnick", description="📝 Установить ник другому"),
        BotCommand(command="nicklist", description="📋 Список ников"),
        
        # Звезды и топы
        BotCommand(command="top", description="🏆 Топ пользователей"),
        BotCommand(command="addstar", description="⭐️ Добавить звезды"),
        BotCommand(command="removestar", description="➖ Убрать звезды"),
        BotCommand(command="setstars", description="⚙️ Установить звезды"),
        
        # Управление ролями
        BotCommand(command="makezam", description="👑 Назначить зама"),
        BotCommand(command="removezam", description="🗑 Снять зама"),
        
        # Отчеты
        BotCommand(command="ot", description="📊 Меню отчетов"),
        BotCommand(command="otlist", description="📋 Список всех отчетов"),
        BotCommand(command="addot", description="📝 Добавить отчет"),
        BotCommand(command="removeot", description="🗑 Удалить отчет"),
        BotCommand(command="otinfo", description="ℹ️ Настройки отчетов"),
        BotCommand(command="setot", description="⚙️ Меню настроек отчетов"),
        
        # Задачи
        BotCommand(command="tasklist", description="📋 Список задач"),
        BotCommand(command="addtask", description="➕ Добавить задачу"),
        BotCommand(command="taskcomplete", description="✅ Выполнить задачу"),
        BotCommand(command="removetask", description="🗑 Удалить задачу"),
        
        # Администрирование
        BotCommand(command="users", description="👥 Все пользователи"),
        BotCommand(command="bdusers", description="👥 Расширенный список"),
        BotCommand(command="bdinfo", description="ℹ️ Информация о БД"),
        BotCommand(command="history", description="📜 История пользователя"),
        BotCommand(command="adduser", description="➕ Добавить пользователя"),
        BotCommand(command="removeuser", description="🗑 Удалить пользователя"),
        BotCommand(command="topclear", description="🔄 Очистить данные топа"),
        BotCommand(command="refresh_top", description="🔄 Обновить снимки топа"),
        
        # Настройки
        BotCommand(command="setnorm", description="📊 Установить норму"),
        BotCommand(command="setbonus", description="💰 Установить бонус"),
        BotCommand(command="setsalary", description="💵 Установить зарплату"),
    ]
    
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.system(f"✅ Установлено команд: {len(commands)}")
    except TelegramAPIError as e:
        logger.error(f"❌ Ошибка установки команд: {e}")


async def shutdown():
    """Остановка бота"""
    logger.system("🛑 Остановка бота...")
    await bot.session.close()
    logger.system("👋 Бот остановлен")


async def main():
    """Основная функция"""
    logger.system("🚀 Запуск бота...")
    
    # Информация о системе
    logger.system(f"Python: {sys.version.split()[0]}, Platform: {platform.platform()}")
    logger.system(f"Admin chat: {config.ADMIN_CHAT_ID}, Tasks chat: {config.TASKS_CHAT_ID}")
    
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(0.5)
    
    # Инициализируем БД
    await init_db()
    logger.system("✅ База данных инициализирована")
    
    # Устанавливаем команды
    await set_commands()
    
    # Запускаем фоновые задачи
    asyncio.create_task(check_overdue_notifications(bot))
    asyncio.create_task(check_upcoming_tasks(bot))
    logger.system("✅ Фоновые задачи запущены")
    
    logger.system("✅ Бот готов к работе!")
    logger.system("📡 Запуск polling...")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.system("🛑 Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.system("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)