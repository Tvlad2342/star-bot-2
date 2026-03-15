"""
Инлайн-клавиатуры для отчетов
"""

from aiogram import Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

router = Router()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню отчетов"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        ("📋 ПРОСМОТР ОТЧЕТОВ", "view_reports"),
        ("➕ ДОБАВИТЬ ОТЧЕТ", "add_report"),
        ("🗑 УДАЛИТЬ ОТЧЕТ", "delete_report"),
        ("❌ ЗАКРЫТЬ", "close")
    ]
    
    for text, callback in buttons:
        builder.row(InlineKeyboardButton(text=text, callback_data=callback))
    
    return builder.as_markup()


def get_dates_keyboard(dates: List[str], prefix: str = "date", show_back: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для выбора даты из списка существующих отчетов"""
    builder = InlineKeyboardBuilder()
    
    for date in dates:
        display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%y")
        callback = f"{prefix}_{date}"
        builder.row(InlineKeyboardButton(text=display_date, callback_data=callback))
    
    # Кнопка "Другая дата"
    builder.row(InlineKeyboardButton(
        text="📅 Другая дата", 
        callback_data=f"{prefix}_custom"
    ))
    
    # Кнопка "Назад" если нужно
    if show_back:
        builder.row(InlineKeyboardButton(
            text="🔙 Назад", 
            callback_data="reports_main_menu"
        ))
    
    return builder.as_markup()


def get_last_7_days_keyboard(prefix: str = "date") -> InlineKeyboardMarkup:
    """Клавиатура с последними 7 днями (начиная с сегодня)"""
    builder = InlineKeyboardBuilder()
    
    today = datetime.now()
    
    for i in range(7):
        date = today - timedelta(days=i)
        display = date.strftime("%d.%m.%y")
        date_str = date.strftime("%Y-%m-%d")
        callback = f"{prefix}_{date_str}"
        builder.row(InlineKeyboardButton(text=display, callback_data=callback))
    
    # Кнопка "Другая дата"
    builder.row(InlineKeyboardButton(
        text="📅 Другая дата", 
        callback_data=f"{prefix}_custom"
    ))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(
        text="🔙 Назад", 
        callback_data="reports_main_menu"
    ))
    
    return builder.as_markup()


def get_zams_keyboard(zams: List[Tuple[int, str]], date: str) -> InlineKeyboardMarkup:
    """Клавиатура для выбора зама"""
    builder = InlineKeyboardBuilder()
    
    for zam_id, zam_name in zams:
        callback = f"select_zam_{zam_id}_{date}"
        builder.row(InlineKeyboardButton(text=zam_name[:30], callback_data=callback))
    
    builder.row(InlineKeyboardButton(
        text="🔙 Назад к датам", 
        callback_data="add_report"
    ))
    
    return builder.as_markup()


def get_invites_keyboard(zam_id: int, date: str) -> InlineKeyboardMarkup:
    """Клавиатура для ввода количества инвайтов"""
    builder = InlineKeyboardBuilder()
    
    # Быстрый ввод популярных значений
    quick_values = [5, 10, 15, 20, 25, 30, 40, 50]
    
    # Распределяем по рядам (по 4 кнопки)
    for i in range(0, len(quick_values), 4):
        row = quick_values[i:i+4]
        buttons = []
        for val in row:
            callback = f"invite_{zam_id}_{date}_{val}"
            buttons.append(InlineKeyboardButton(text=str(val), callback_data=callback))
        builder.row(*buttons)
    
    # Кнопка для ручного ввода
    builder.row(InlineKeyboardButton(
        text="✏️ Ввести вручную", 
        callback_data=f"invite_manual_{zam_id}_{date}"
    ))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(
        text="🔙 Назад к замам", 
        callback_data=f"select_date_back_{date}"
    ))
    
    return builder.as_markup()


def get_back_keyboard(target: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура с кнопкой назад"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=target))
    return builder.as_markup()


def get_custom_date_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для режима ручного ввода даты"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="reports_main_menu"))
    return builder.as_markup()