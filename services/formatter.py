"""
Функции для форматирования сообщений (расширенная версия)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from utils.constants import STYLES, DIVIDER
import re


def create_progress_bar(current: int, maximum: int, length: int = 10, 
                       filled: str = "▰", empty: str = "▱") -> str:
    """Создает визуальный прогресс-бар с настраиваемыми символами"""
    if maximum <= 0:
        return empty * length
    filled_count = min(int((current / maximum) * length), length)
    return filled * filled_count + empty * (length - filled_count)


def format_message(title: str, content: str, style: str = 'info', 
                   add_divider: bool = True) -> str:
    """Форматирует сообщение в едином стиле"""
    emoji = STYLES.get(style, 'ℹ️')
    
    if not title.startswith(tuple(STYLES.values())):
        title = f"{emoji} {title}"
    
    result = f"<b>{title}</b>\n{content}"
    if add_divider:
        result += f"\n{DIVIDER}"
    
    return result


def format_error_message(error_text: str, details: Optional[str] = None) -> str:
    """Форматирует сообщение об ошибке с деталями"""
    result = f"{STYLES['error']} <b>ОШИБКА</b>\n{error_text}"
    if details:
        result += f"\n<i>{details}</i>"
    return result + f"\n{DIVIDER}"


def format_success_message(success_text: str, details: Optional[str] = None) -> str:
    """Форматирует сообщение об успехе"""
    result = f"{STYLES['success']} <b>УСПЕШНО</b>\n{success_text}"
    if details:
        result += f"\n<i>{details}</i>"
    return result + f"\n{DIVIDER}"


def format_time_remaining(deadline_str: str, full_format: bool = False) -> str:
    """Форматирует оставшееся время с разными форматами"""
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        
        if deadline < now:
            diff = now - deadline
            if diff.days > 0:
                return f"{STYLES['warning']} Просрочено на {diff.days}д"
            elif diff.seconds // 3600 > 0:
                return f"{STYLES['warning']} Просрочено на {diff.seconds // 3600}ч"
            else:
                return f"{STYLES['warning']} Просрочено"
        
        diff = deadline - now
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        if full_format:
            if diff.days > 0:
                return f"{STYLES['time']} {diff.days} дн {hours} ч {minutes} мин"
            elif hours > 0:
                return f"{STYLES['time']} {hours} ч {minutes} мин"
            else:
                return f"{STYLES['time']} {minutes} мин"
        else:
            if diff.days > 0:
                return f"{STYLES['time']} {diff.days}д {hours}ч"
            elif hours > 0:
                return f"{STYLES['time']} {hours}ч {minutes}мин"
            else:
                return f"{STYLES['time']} {minutes}мин"
    except Exception as e:
        return f"{STYLES['time']} Неизвестно"


def format_date(timestamp: str, include_time: bool = True) -> str:
    """Форматирует дату в читаемый вид"""
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        if include_time:
            return dt.strftime("%d.%m.%Y %H:%M")
        return dt.strftime("%d.%m.%Y")
    except:
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d")
            return dt.strftime("%d.%m.%Y")
        except:
            return timestamp


def format_short_date(date_str: str) -> str:
    """Форматирует короткую дату"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except:
        return date_str


def format_number(num: int, with_currency: bool = False) -> str:
    """Форматирует число с разделителями и опциональной валютой"""
    formatted = f"{num:,}".replace(",", ".")
    if with_currency:
        return f"{formatted}₸"
    return formatted


def get_medal_icon(position: int) -> str:
    """Возвращает эмодзи для позиции в топе"""
    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
        4: "4️⃣",
        5: "5️⃣",
        6: "6️⃣",
        7: "7️⃣",
        8: "8️⃣",
        9: "9️⃣",
        10: "🔟"
    }
    return medals.get(position, f"{position}.")


def format_table(headers: List[str], rows: List[List[str]], 
                max_width: int = 30) -> str:
    """Форматирует данные в виде таблицы"""
    if not rows:
        return ""
    
    # Определяем ширину колонок
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
    
    # Ограничиваем ширину
    col_widths = [min(w, max_width) for w in col_widths]
    
    # Формируем заголовок
    header = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    separator = "-+-".join("-" * w for w in col_widths)
    
    lines = [header, separator]
    
    # Добавляем строки
    for row in rows:
        truncated_row = []
        for cell, width in zip(row, col_widths):
            if len(cell) > width:
                cell = cell[:width-3] + "..."
            truncated_row.append(cell.ljust(width))
        lines.append(" | ".join(truncated_row))
    
    return "```\n" + "\n".join(lines) + "\n```"


def escape_html(text: str) -> str:
    """Экранирует HTML спецсимволы"""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def format_user_mention(user_id: int, name: str) -> str:
    """Форматирует упоминание пользователя"""
    return f'<a href="tg://user?id={user_id}">{escape_html(name)}</a>'


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезает текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_list(items: List[str], bullet: str = "•") -> str:
    """Форматирует список"""
    return "\n".join(f"{bullet} {item}" for item in items)


def format_key_value(key: str, value: Any, separator: str = ":") -> str:
    """Форматирует пару ключ-значение"""
    return f"<b>{key}</b>{separator} {value}"