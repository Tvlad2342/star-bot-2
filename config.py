import os
from dotenv import load_dotenv
from typing import List

# Загружаем переменные из .env файла
load_dotenv()


class Config:
    """Класс конфигурации бота"""
    
    def __init__(self):
        # Токен бота
        self.TOKEN = os.getenv("BOT_TOKEN")
        
        if not self.TOKEN:
            raise ValueError("Не найден BOT_TOKEN в файле .env")
        
        # ID основателей
        self.FOUNDER_IDS = self._load_founder_ids()
        
        # ID чатов
        self.ADMIN_CHAT_ID = self._safe_int(os.getenv("ADMIN_CHAT_ID"), 0)
        self.TASKS_CHAT_ID = os.getenv("TASKS_CHAT_ID", "0")  # может быть с топиком
        
        # Путь к базе данных
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")
        
        # Настройки задач
        self.OVERDUE_CHECK_INTERVAL = self._safe_int(os.getenv("OVERDUE_CHECK_INTERVAL"), 300)
        self.UPCOMING_CHECK_INTERVAL = self._safe_int(os.getenv("UPCOMING_CHECK_INTERVAL"), 300)
        
        print(f"✅ Конфигурация загружена:")
        print(f"   Founder IDs: {self.FOUNDER_IDS}")
        print(f"   ADMIN_CHAT_ID: {self.ADMIN_CHAT_ID}")
        print(f"   TASKS_CHAT_ID: {self.TASKS_CHAT_ID}")
    
    def _load_founder_ids(self) -> List[int]:
        """Загружает ID основателей"""
        founder_ids = []
        i = 1
        
        while True:
            founder_id = os.getenv(f"FOUNDER_ID_{i}")
            if founder_id:
                try:
                    founder_ids.append(int(founder_id))
                    i += 1
                except ValueError:
                    i += 1
            else:
                break
        
        return founder_ids
    
    def _safe_int(self, value: str, default: int) -> int:
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default


config = Config()

# Экспортируем переменные
TOKEN = config.TOKEN
FOUNDER_IDS = config.FOUNDER_IDS
ADMIN_CHAT_ID = config.ADMIN_CHAT_ID
TASKS_CHAT_ID = config.TASKS_CHAT_ID
DATABASE_PATH = config.DATABASE_PATH
OVERDUE_CHECK_INTERVAL = config.OVERDUE_CHECK_INTERVAL
UPCOMING_CHECK_INTERVAL = config.UPCOMING_CHECK_INTERVAL