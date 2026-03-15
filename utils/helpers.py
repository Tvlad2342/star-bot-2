"""
Вспомогательные функции (расширенная версия)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict, Union
import re
import hashlib
import json
import random
import string
from collections import defaultdict


def escape_username(username: Optional[str]) -> str:
    """Экранирует юзернейм для отображения без пинга"""
    if not username:
        return "Неизвестно"
    if username.startswith("id"):
        return username
    return f"@{username}"


def parse_date(date_str: str) -> Optional[str]:
    """Парсит дату из формата ДД.ММ.ГГ в YYYY-MM-DD"""
    try:
        # Поддерживаем разные форматы
        date_str = date_str.strip()
        
        # ДД.ММ.ГГ или ДД.ММ.ГГГГ
        if "." in date_str:
            parts = date_str.split(".")
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # ДД-ММ-ГГ
        elif "-" in date_str:
            parts = date_str.split("-")
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # ДД/ММ/ГГ
        elif "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    except:
        return None


def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """Парсит дату и время из строки"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%y %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d.%m.%y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    return None


def validate_invites(count: int) -> bool:
    """Проверяет корректность количества инвайтов"""
    return 0 <= count <= 1000


def validate_hours(hours: int) -> bool:
    """Проверяет корректность количества часов"""
    return 1 <= hours <= 24


def validate_task_number(number: int) -> bool:
    """Проверяет корректность номера задачи"""
    return 1 <= number <= 999


def validate_amount(amount: int, min_val: int = -1000, max_val: int = 1000) -> bool:
    """Проверяет корректность количества звезд"""
    return min_val <= amount <= max_val


def validate_username(username: str) -> bool:
    """Проверяет корректность Telegram username"""
    if not username:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_]{5,32}$', username))


def validate_nickname(nickname: str) -> bool:
    """Проверяет корректность ника"""
    if len(nickname) < 2 or len(nickname) > 32:
        return False
    return bool(re.match(r'^[a-zA-Zа-яА-Я0-9\s\-]+$', nickname))


def split_message(text: str, max_length: int = 4096) -> List[str]:
    """Разбивает длинное сообщение на части"""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]


def generate_random_string(length: int = 8) -> str:
    """Генерирует случайную строку"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def create_callback_hash(data: Dict[str, Any]) -> str:
    """Создает короткий хеш для callback_data"""
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(data_str.encode()).hexdigest()[:8]


def extract_mentions(text: str) -> List[str]:
    """Извлекает все упоминания (@username) из текста"""
    return re.findall(r'@(\w+)', text)


def extract_numbers(text: str) -> List[int]:
    """Извлекает все числа из текста"""
    return [int(x) for x in re.findall(r'\d+', text)]


def safe_int(value: Any, default: int = 0) -> int:
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def group_by_key(items: List[Any], key_func) -> Dict[Any, List[Any]]:
    """Группирует элементы по ключу"""
    result = defaultdict(list)
    for item in items:
        result[key_func(item)].append(item)
    return dict(result)


def get_period_dates(period: str) -> tuple:
    """Возвращает начальную и конечную дату для периода"""
    today = datetime.now()
    
    periods = {
        'day': (today, today),
        'yesterday': (today - timedelta(days=1), today - timedelta(days=1)),
        'week': (today - timedelta(days=7), today),
        'month': (today - timedelta(days=30), today),
        'year': (today - timedelta(days=365), today)
    }
    
    if period in periods:
        start, end = periods[period]
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    
    return None, None


def format_size(size_bytes: int) -> str:
    """Форматирует размер файла"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"