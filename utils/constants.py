"""
Все константы, которые используются в боте
"""

from typing import Dict
from enum import IntEnum, Enum


class Style(str, Enum):
    """Стили оформления с эмодзи"""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    STATS = "📊"
    TASK = "📋"
    STAR = "⭐️"
    USER = "👤"
    ADMIN = "👑"
    CROWN = "👑"
    MONEY = "💰"
    TIME = "⏰"
    REPORT = "📝"
    TOP = "🏆"
    SETTINGS = "⚙️"
    HISTORY = "📜"
    ADD = "➕"
    REMOVE = "➖"
    EDIT = "✏️"
    CALENDAR = "📅"
    LIST = "📋"
    CHART = "📈"


# Для обратной совместимости
STYLES = {name.lower(): value.value for name, value in Style.__members__.items()}


class Role(IntEnum):
    """Роли пользователей"""
    USER = 0
    ZAM_1 = 1
    ZAM_2 = 2
    ZAM_3 = 3
    ZAM_4 = 4
    ZAM_5 = 5
    FOUNDER = 6
    
    @property
    def name_ru(self) -> str:
        """Русское название роли"""
        names = {
            0: "Пользователь",
            1: "ZAM 1",
            2: "ZAM 2",
            3: "ZAM 3",
            4: "ZAM 4",
            5: "ZAM 5",
            6: "Основатель"
        }
        return names.get(self.value, "Неизвестно")
    
    @property
    def emoji(self) -> str:
        """Эмодзи роли"""
        emojis = {
            0: "👤",
            1: "🌟",
            2: "🌟🌟",
            3: "🌟🌟🌟",
            4: "🌟🌟🌟🌟",
            5: "🌟🌟🌟🌟🌟",
            6: "👑"
        }
        return emojis.get(self.value, "👤")


# Для обратной совместимости
ROLES = {role.value: role.name_ru for role in Role}
ROLE_EMOJIS = {role.value: role.emoji for role in Role}


class TaskStatus(str, Enum):
    """Статусы задач"""
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    
    @property
    def display_name(self) -> str:
        """Отображаемое название статуса"""
        names = {
            "pending": "⏳ В работе",
            "completed": "✅ Выполнена",
            "overdue": "⚠️ Просрочена"
        }
        return names.get(self.value, self.value)
    
    @property
    def emoji(self) -> str:
        """Эмодзи статуса"""
        emojis = {
            "pending": "⏳",
            "completed": "✅",
            "overdue": "⚠️"
        }
        return emojis.get(self.value, "❓")


# Для обратной совместимости
TASK_STATUS = {status.value: status.display_name for status in TaskStatus}


# Минимальные уровни для команд
# Убедитесь что в COMMAND_PERMISSIONS есть все команды:
COMMAND_PERMISSIONS = {
    # Уровень 0+ (для всех, даже без роли)
    'start': 0,
    'addnick': 0,
    
    # Уровень 1+ (ZAM 1 и выше)
    'help': 1,
    'stats': 1,
    'removenick_self': 1,
    'tasklist': 1,
    'taskcomplete': 1,
    
    # Уровень 3+ (ZAM 3 и выше)
    'addtask': 3,
    
    # Уровень 4+ (ZAM 4 и выше)
    'top': 4,
    'nicklist': 4,
    
    # Уровень 5+ (ZAM 5 и выше)
    'stats_with_user': 5,
    'addstar': 5,
    'removestar': 5,
    'makezam': 5,
    'removezam': 5,
    'removetask': 5,
    'ot': 5,
    'otlist': 5,
    'addot': 5,
    'removeot': 5,
    
    # Уровень 6 (Основатель)
    'setstars': 6,
    'history': 6,
    'historyall': 6,
    'users': 6,
    'bdusers': 6,
    'bdinfo': 6,
    'removeuser': 6,
    'adduser': 6,
    'setnick': 6,
    'removenick_other': 6,
    'topclear': 6,
    'refresh_top': 6,
    'setnorm': 6,
    'setbonus': 6,
    'setsalary': 6,
    'otinfo': 6,
    'setot': 6,
    'logs': 6,
    'about': 6,
}

# Оформление
DIVIDER = "══════════════════════════════"
LINE = "──────────────────────────────"


# ========== ДОБАВЛЕННЫЕ КЛАССЫ КОНСТАНТ ==========

class ReportConstants:
    """Константы для отчетов"""
    MIN_INVITES = 0
    MAX_INVITES = 1000
    DEFAULT_NORM = 5
    DEFAULT_BONUS = 50
    MAX_BONUS = 1000
    
    # Таблица расчета звезд
    STARS_TABLE = [
        (100, 39), (95, 37), (90, 35), (85, 33), (80, 31),
        (75, 29), (70, 27), (65, 25), (60, 23), (55, 21),
        (50, 19), (45, 17), (40, 15), (35, 13), (30, 11),
        (25, 9), (20, 7), (15, 5), (10, 3), (5, 1)
    ]
    
    # Зарплаты по умолчанию
    DEFAULT_SALARIES = {
        1: 300000,
        2: 400000,
        3: 500000,
        4: 600000,
        5: 700000
    }


class TaskConstants:
    """Константы для задач"""
    MIN_HOURS = 1
    MAX_HOURS = 24
    MIN_TASK_NUMBER = 1
    MAX_TASK_NUMBER = 999
    
    # Интервалы проверки (в секундах)
    OVERDUE_CHECK_INTERVAL = 300  # 5 минут
    UPCOMING_CHECK_INTERVAL = 300  # 5 минут
    
    # За сколько минут до дедлайна считать задачу срочной
    URGENT_THRESHOLD_MINUTES = 60


class CacheConstants:
    """Константы для кэширования"""
    USER_CACHE_TTL = 300  # 5 минут
    SETTINGS_CACHE_TTL = 300  # 5 минут
    PERMISSION_CACHE_TTL = 300  # 5 минут
    MAX_CACHE_SIZE = 1000


class PaginationConstants:
    """Константы для пагинации"""
    ITEMS_PER_PAGE = 10
    MAX_PAGES = 10