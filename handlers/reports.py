"""
Команды для работы с отчетами с инлайн-клавиатурами и FSM
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from database.db import (
    add_report, get_reports_by_date, get_reports_for_period,
    delete_reports_by_date, get_all_users, get_all_reports_dates,
    get_all_reports_grouped_by_month, get_user_by_id
)
from services.calculator import SalaryCalculator
from services.formatter import format_number, format_short_date
from utils.constants import STYLES, DIVIDER, ROLE_EMOJIS
from utils.helpers import validate_invites, parse_date, split_message
from handlers.reports_keyboard import (
    get_main_menu_keyboard, get_dates_keyboard, get_last_7_days_keyboard,
    get_zams_keyboard, get_invites_keyboard, get_back_keyboard,
    get_custom_date_back_keyboard
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import User
from collections import defaultdict
from utils.logger import send_admin_log

router = Router()
calculator = SalaryCalculator()


# ========== FSM СОСТОЯНИЯ ==========

class ReportStates(StatesGroup):
    """Состояния для добавления отчета"""
    choosing_action = State()
    choosing_date = State()
    choosing_zam = State()
    entering_invites = State()
    waiting_for_custom_date = State()


# ========== ГЛАВНОЕ МЕНЮ ==========

@router.message(Command("ot"))
async def ot_cmd(msg: Message, state: FSMContext):
    """Главная команда для работы с отчетами"""
    parts = msg.text.split()
    
    # ЕСЛИ ЕСТЬ ДАТА В КОМАНДЕ - показываем отчет за эту дату
    if len(parts) > 1:
        date_str = parts[1]
        date = parse_date(date_str)
        
        if date:
            # Проверяем, есть ли отчеты за эту дату
            reports = await get_reports_by_date(date)
            if reports:
                # Показываем отчет за дату (не меню!)
                await show_report_by_date_command(msg, date, state)
            else:
                await msg.reply(f"{STYLES['info']} Нет отчетов за {date_str}", parse_mode="HTML")
        else:
            await msg.reply(
                f"{STYLES['error']} Неверный формат даты. Используйте ДД.ММ.ГГ\n"
                f"Пример: /ot 28.02.26",
                parse_mode="HTML"
            )
        return
    
    # ЕСЛИ НЕТ ДАТЫ - показываем меню
    await state.clear()
    await state.set_state(ReportStates.choosing_action)
    
    text = (
        f"{STYLES['report']} <b>МЕНЮ ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
        f"Выберите действие:"
    )
    
    await msg.reply(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


# Новая функция для показа отчета по команде /ot с датой
async def show_report_by_date_command(message: Message, date: str, state: FSMContext):
    """Показывает отчет за дату (вызывается из команды /ot с датой)"""
    reports = await get_reports_by_date(date)
    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    
    # Заголовок
    text = f"<b>Суточный отчет по инвайтам</b>\n"
    text += f"<b>за {display_date}</b>\n\n"
    
    total_invites = 0
    total_salary = 0
    
    for i, report in enumerate(reports, 1):
        await calculator.load_settings()
        calc = await calculator.calculate(report.zam_level or 1, report.invites_count)
        
        zam_name = report.nickname if report.nickname else f"@{report.username}"
        zam_level = report.zam_level or 1
        
        text += f"{i}. <b>{zam_name}</b>[{zam_level}] (@{report.username})\n"
        
        # Норма
        if calc['salary_for_norm'] > 0:
            norm_status = "Выполнена"
            norm_salary = f"+{format_number(calc['salary_for_norm'])}"
        else:
            norm_status = "Не выполнена"
            norm_salary = f"+0"
        
        text += f"   Норма ({calc['norm']}): {norm_status} - ({norm_salary})\n"
        
        # Сверх норма
        if calc['extra_invites'] > 0:
            text += f"   Сверх норма: {calc['extra_invites']} (+{format_number(calc['bonus_salary'])})\n"
        
        # Итог
        stars_text = f"+{calc['total_stars']}⭐️" if calc['total_stars'] > 0 else "-1⭐️"
        text += f"   Итог зп: +{format_number(calc['total_salary'])} | {stars_text}\n\n"
        
        total_invites += report.invites_count
        total_salary += calc['total_salary']
    
    # Итоговый блок
    text += f"<b>Итоговый инвайт за сутки:</b>\n"
    text += f"Кол-во человек: {total_invites}\n"
    text += f"Заработано замами: {format_number(total_salary)}"
    
    await message.reply(text, parse_mode="HTML")


@router.callback_query(F.data == "reports_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню отчетов"""
    await callback.answer()
    
    # Проверяем текущее состояние
    current_state = await state.get_state()
    if current_state == ReportStates.choosing_action:
        await callback.answer("Вы уже в главном меню")
        return
    
    await state.set_state(ReportStates.choosing_action)
    
    text = (
        f"{STYLES['report']} <b>МЕНЮ ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
        f"Выберите действие:"
    )
    
    try:
        await callback.message.edit_text(
            text, 
            reply_markup=get_main_menu_keyboard(), 
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data == "close")
async def close_menu(callback: CallbackQuery, state: FSMContext):
    """Закрытие меню"""
    await callback.answer()
    await state.clear()
    await callback.message.delete()


# ========== ПРОСМОТР ОТЧЕТОВ ==========

@router.callback_query(F.data == "view_reports")
async def view_reports_start(callback: CallbackQuery, state: FSMContext):
    """Начало просмотра отчетов"""
    await callback.answer()
    
    # Проверяем текущее состояние
    current_state = await state.get_state()
    if current_state == ReportStates.choosing_date:
        await callback.answer("Вы уже в режиме выбора даты")
        return
    
    await state.set_state(ReportStates.choosing_date)
    
    # Получаем все даты с отчетами за последние 7 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    reports_dates = await get_all_reports_dates(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )
    
    if not reports_dates:
        text = (
            f"{STYLES['calendar']} <b>ПРОСМОТР ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
            f"За последние 7 дней нет отчетов"
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )
        return
    
    text = (
        f"{STYLES['calendar']} <b>ПРОСМОТР ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
        f"Выберите дату:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_dates_keyboard(reports_dates, prefix="view_date"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_date_"))
async def view_report_by_date(callback: CallbackQuery, state: FSMContext):
    """Просмотр отчета за конкретную дату"""
    await callback.answer()
    
    date = callback.data.replace("view_date_", "")
    
    if date == "custom":
        await state.set_state(ReportStates.waiting_for_custom_date)
        await callback.message.edit_text(
            f"{STYLES['info']} <b>ВВЕДИТЕ ДАТУ</b>\n{DIVIDER}\n\n"
            f"Отправьте дату в формате <b>ДД.ММ.ГГ</b>\n"
            f"Например: <code>15.05.24</code>\n\n"
            f"Или нажмите кнопку назад:",
            reply_markup=get_custom_date_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await show_report(callback.message, date, state)


async def show_report(message: Message, date: str, state: FSMContext):
    """Показывает отчет за дату (для инлайн-режима)"""
    reports = await get_reports_by_date(date)
    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    
    if not reports:
        text = (
            f"{STYLES['calendar']} <b>ОТЧЕТ ЗА {display_date}</b>\n{DIVIDER}\n\n"
            f"❌ Нет отчетов за эту дату"
        )
        await message.edit_text(
            text,
            reply_markup=get_back_keyboard("view_reports"),
            parse_mode="HTML"
        )
        return
    
    # Заголовок
    text = f"<b>Суточный отчет по инвайтам</b>\n"
    text += f"<b>за {display_date}</b>\n\n"
    
    total_invites = 0
    total_salary = 0
    
    for i, report in enumerate(reports, 1):
        await calculator.load_settings()
        calc = await calculator.calculate(report.zam_level or 1, report.invites_count)
        
        zam_name = report.nickname if report.nickname else f"@{report.username}"
        zam_level = report.zam_level or 1
        
        text += f"{i}. <b>{zam_name}</b>[{zam_level}] (@{report.username})\n"
        
        # Норма
        if calc['salary_for_norm'] > 0:
            norm_status = "Выполнена"
            norm_salary = f"+{format_number(calc['salary_for_norm'])}"
        else:
            norm_status = "Не выполнена"
            norm_salary = f"+0"
        
        text += f"   Норма ({calc['norm']}): {norm_status} - ({norm_salary})\n"
        
        # Сверх норма
        if calc['extra_invites'] > 0:
            text += f"   Сверх норма: {calc['extra_invites']} (+{format_number(calc['bonus_salary'])})\n"
        
        # Итог
        stars_text = f"+{calc['total_stars']}⭐️" if calc['total_stars'] > 0 else "-1⭐️"
        text += f"   Итог зп: +{format_number(calc['total_salary'])} | {stars_text}\n\n"
        
        total_invites += report.invites_count
        total_salary += calc['total_salary']
    
    # Итоговый блок
    text += f"<b>Итоговый инвайт за сутки:</b>\n"
    text += f"Кол-во человек: {total_invites}\n"
    text += f"Заработано замами: {format_number(total_salary)}"
    
    # Создаем клавиатуру с кнопкой назад
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад к датам", callback_data="view_reports"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="reports_main_menu"))
    
    try:
        await message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise


# ========== ДОБАВЛЕНИЕ ОТЧЕТА ==========

@router.callback_query(F.data == "add_report")
async def add_report_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления отчета"""
    await callback.answer()
    await state.set_state(ReportStates.choosing_date)
    
    text = (
        f"{STYLES['add']} <b>ДОБАВЛЕНИЕ ОТЧЕТА</b>\n{DIVIDER}\n\n"
        f"Выберите дату:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_last_7_days_keyboard(prefix="add_date"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("add_date_"))
async def select_date_for_report(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для отчета"""
    await callback.answer()
    
    date = callback.data.replace("add_date_", "")
    
    if date == "custom":
        await state.set_state(ReportStates.waiting_for_custom_date)
        await callback.message.edit_text(
            f"{STYLES['info']} <b>ВВЕДИТЕ ДАТУ</b>\n{DIVIDER}\n\n"
            f"Отправьте дату в формате <b>ДД.ММ.ГГ</b>\n"
            f"Например: <code>15.05.24</code>\n\n"
            f"Или нажмите кнопку назад:",
            reply_markup=get_custom_date_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    try:
        datetime.strptime(date, "%Y-%m-%d")
        await state.update_data(report_date=date)
        await show_zams_selection(callback.message, date, state)
    except ValueError:
        await callback.message.edit_text(
            f"{STYLES['error']} <b>ОШИБКА</b>\n{DIVIDER}\n\n"
            f"Неверный формат даты.",
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )


@router.message(ReportStates.waiting_for_custom_date)
async def process_custom_date(msg: Message, state: FSMContext):
    """Обработка ручного ввода даты"""
    date_str = msg.text.strip()
    date = parse_date(date_str)
    
    if not date:
        await msg.reply(
            f"{STYLES['error']} <b>ОШИБКА</b>\n{DIVIDER}\n\n"
            f"Неверный формат даты. Используйте ДД.ММ.ГГ\n"
            f"Например: 15.05.24",
            reply_markup=get_custom_date_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(report_date=date)
    
    # Получаем текущее состояние
    current_state = await state.get_state()
    
    if current_state == ReportStates.waiting_for_custom_date:
        await state.set_state(ReportStates.choosing_zam)
        await show_zams_selection(msg, date, state)
    else:
        await show_report(msg, date, state)


async def show_zams_selection(message: Message, date: str, state: FSMContext):
    """Показывает выбор замов для отчета"""
    await state.set_state(ReportStates.choosing_zam)
    
    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    
    all_users = await get_all_users()
    zams = [(u.id, u.display_name) for u in all_users if 1 <= u.role <= 5]
    
    if not zams:
        await message.edit_text(
            f"{STYLES['error']} ❌ Нет замов для добавления отчета",
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    text = (
        f"{STYLES['add']} <b>ДОБАВЛЕНИЕ ОТЧЕТА ЗА {display_date}</b>\n{DIVIDER}\n\n"
        f"Выберите зама:"
    )
    
    await message.edit_text(
        text,
        reply_markup=get_zams_keyboard(zams, date),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("select_zam_"))
async def select_zam_for_report(callback: CallbackQuery, state: FSMContext):
    """Выбор зама для отчета"""
    await callback.answer()
    
    parts = callback.data.split("_")
    zam_id = int(parts[2])
    date = parts[3]
    
    await state.update_data(zam_id=zam_id, date=date)
    await state.set_state(ReportStates.entering_invites)
    
    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    
    all_users = await get_all_users()
    zam = next((u for u in all_users if u.id == zam_id), None)
    
    text = (
        f"{STYLES['add']} <b>ОТЧЕТ ДЛЯ {zam.display_name if zam else 'Зама'}</b>\n"
        f"<b>За {display_date}</b>\n{DIVIDER}\n\n"
        f"Выберите количество инвайтов\n"
        f"или введите число от 0 до 1000:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_invites_keyboard(zam_id, date),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("invite_"))
async def process_invites_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора инвайтов"""
    parts = callback.data.split("_")
    
    if parts[1] == "manual":
        await callback.answer()
        await callback.message.edit_text(
            f"{STYLES['info']} <b>ВВЕДИТЕ КОЛИЧЕСТВО</b>\n{DIVIDER}\n\n"
            f"Отправьте число инвайтов (от 0 до 1000):\n\n"
            f"Или нажмите кнопку назад:",
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )
        return
    
    try:
        zam_id = int(parts[1])
        date = parts[2]
        invites = int(parts[3])
        
        await save_report(callback.message, zam_id, date, invites, state, callback.bot)
        await callback.answer(f"✅ Добавлено: {invites} инвайтов")
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка формата данных")


@router.message(ReportStates.entering_invites)
async def process_manual_invites(msg: Message, state: FSMContext, bot: Bot):
    """Обработка ручного ввода инвайтов"""
    try:
        invites = int(msg.text.strip())
        
        if not validate_invites(invites):
            await msg.reply(
                f"{STYLES['error']} ❌ Количество должно быть от 0 до 1000\n\n"
                f"Попробуйте снова:",
                reply_markup=get_back_keyboard("reports_main_menu"),
                parse_mode="HTML"
            )
            return
        
        data = await state.get_data()
        zam_id = data.get('zam_id')
        date = data.get('date')
        
        await save_report(msg, zam_id, date, invites, state, bot)
        
    except ValueError:
        await msg.reply(
            f"{STYLES['error']} ❌ Введите число\n\n"
            f"Попробуйте снова:",
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )


async def save_report(message: Message, zam_id: int, date: str, invites: int, state: FSMContext, bot: Bot):
    """Сохраняет отчет в БД"""
    await add_report(date, zam_id, invites)
    
    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    
    all_users = await get_all_users()
    zam = next((u for u in all_users if u.id == zam_id), None)
    
    # Получаем пользователя из БД по ID
    user_id = message.from_user.id
    user = await get_user_by_id(user_id)
    
    # Если пользователь не найден в БД, создаем временный объект
    if not user:
        user = User(
            id=user_id,
            username=message.from_user.username or f"id{user_id}",
            stars=0,
            role=0,
            nickname=None
        )
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "📅 Дата отчета": display_date,
        "📊 Инвайтов": str(invites),
        "👤 Зам": zam.display_name if zam else f"id{zam_id}"
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Добавление отчета",
        additional_info=additional_info
    )
    
    text = (
        f"{STYLES['success']} <b>✅ ОТЧЕТ ДОБАВЛЕН</b>\n{DIVIDER}\n\n"
        f"<b>Пользователь:</b> {zam.display_name if zam else f'id{zam_id}'}\n"
        f"<b>Инвайтов:</b> {invites}\n"
        f"<b>Дата:</b> {display_date}\n\n"
        f"Что хотите сделать дальше?"
    )
    
    await message.reply(
        text, 
        reply_markup=get_main_menu_keyboard(), 
        parse_mode="HTML"
    )
    await state.set_state(ReportStates.choosing_action)


# ========== УДАЛЕНИЕ ОТЧЕТОВ ==========

@router.callback_query(F.data == "delete_report")
async def delete_report_start(callback: CallbackQuery, state: FSMContext):
    """Начало удаления отчетов"""
    await callback.answer()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    reports_dates = await get_all_reports_dates(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )
    
    if not reports_dates:
        text = (
            f"{STYLES['remove']} <b>УДАЛЕНИЕ ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
            f"За последние 7 дней нет отчетов для удаления"
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )
        return
    
    text = (
        f"{STYLES['remove']} <b>УДАЛЕНИЕ ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
        f"Выберите дату для удаления:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_dates_keyboard(reports_dates, prefix="delete_date"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("delete_date_"))
async def confirm_delete_report(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления отчета"""
    await callback.answer()
    
    date = callback.data.replace("delete_date_", "")
    
    if date == "custom":
        await state.set_state(ReportStates.waiting_for_custom_date)
        await callback.message.edit_text(
            f"{STYLES['info']} <b>ВВЕДИТЕ ДАТУ</b>\n{DIVIDER}\n\n"
            f"Отправьте дату в формате <b>ДД.ММ.ГГ</b>\n"
            f"Например: <code>15.05.24</code>\n\n"
            f"Или нажмите кнопку назад:",
            reply_markup=get_custom_date_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    try:
        datetime.strptime(date, "%Y-%m-%d")
        display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
        
        text = (
            f"{STYLES['warning']} <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n{DIVIDER}\n\n"
            f"Вы уверены, что хотите удалить все отчеты за {display_date}?"
        )
        
        await state.update_data(delete_date=date)
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_yes"))
        builder.row(InlineKeyboardButton(text="❌ Нет, отмена", callback_data="delete_report"))
        builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="reports_main_menu"))
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await callback.message.edit_text(
            f"{STYLES['error']} <b>ОШИБКА</b>\n{DIVIDER}\n\n"
            f"Неверный формат даты.",
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "confirm_delete_yes")
async def execute_delete_report(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выполнение удаления отчета"""
    await callback.answer()
    
    data = await state.get_data()
    date = data.get('delete_date')
    
    if not date:
        await callback.message.edit_text(
            f"{STYLES['error']} Ошибка: дата не найдена",
            reply_markup=get_back_keyboard("reports_main_menu"),
            parse_mode="HTML"
        )
        return
    
    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    
    await delete_reports_by_date(date)
    
    # Получаем пользователя
    user_id = callback.from_user.id
    user = await get_user_by_id(user_id)
    
    if not user:
        user = User(
            id=user_id,
            username=callback.from_user.username or f"id{user_id}",
            stars=0,
            role=0,
            nickname=None
        )
    
    # Отправляем лог в админ чат в новом формате
    additional_info = {
        "📅 Дата отчета": display_date
    }
    await send_admin_log(
        bot=bot,
        user=user,
        action="Удаление отчета",
        additional_info=additional_info
    )
    
    text = (
        f"{STYLES['success']} <b>✅ ОТЧЕТ УДАЛЕН</b>\n{DIVIDER}\n\n"
        f"Отчет за {display_date} успешно удален\n\n"
        f"Что хотите сделать дальше?"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ReportStates.choosing_action)


# ========== КОМАНДА OTLIST ==========

@router.message(Command("otlist"))
async def otlist_cmd(msg: Message, user: User):
    """Показывает список всех отчетов за все время"""
    
    reports_by_month = await get_all_reports_grouped_by_month()
    
    if not reports_by_month:
        await msg.reply(
            f"{STYLES['info']} <b>СПИСОК ВСЕХ ОТЧЕТОВ</b>\n{DIVIDER}\n\n"
            f"Нет отчетов за все время",
            parse_mode="HTML"
        )
        return
    
    text = f"{STYLES['list']} <b>СПИСОК ВСЕХ ОТЧЕТОВ:</b>\n{DIVIDER}\n\n"
    
    total_reports = 0
    
    for month_key in sorted(reports_by_month.keys(), reverse=True):
        month_data = reports_by_month[month_key]
        month_name = month_data['month_name']
        date_range = month_data['date_range']
        reports = month_data['reports']
        
        text += f"📅 <b>{month_name} ({date_range})</b>\n"
        
        for report_date in sorted(reports, reverse=True):
            display_date = datetime.strptime(report_date, "%Y-%m-%d").strftime("%d.%m.%y")
            text += f"/ot {display_date}\n"
        
        text += "\n"
        total_reports += len(reports)
    
    text += f"{DIVIDER}\n"
    text += f"{STYLES['stats']} <b>Всего отчетов:</b> {total_reports}"
    
    for part in split_message(text):
        await msg.reply(part, parse_mode="HTML")