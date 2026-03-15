"""
Пакет сервисов бота
"""

from services.calculator import SalaryCalculator, get_calculator
from services.permissions import (
    check_permission, role_by_stars, can_edit_user,
    Role, Permission, clear_permission_cache,
    get_users_with_permission, get_highest_role_user
)
from services.formatter import (
    create_progress_bar, format_message, format_error_message,
    format_success_message, format_time_remaining, format_date,
    format_short_date, format_number, get_medal_icon,
    format_table, escape_html, format_user_mention,
    truncate, format_list, format_key_value
)

__all__ = [
    # Calculator
    'SalaryCalculator',
    'get_calculator',
    
    # Permissions
    'check_permission',
    'role_by_stars',
    'can_edit_user',
    'Role',
    'Permission',
    'clear_permission_cache',
    'get_users_with_permission',
    'get_highest_role_user',
    
    # Formatter
    'create_progress_bar',
    'format_message',
    'format_error_message',
    'format_success_message',
    'format_time_remaining',
    'format_date',
    'format_short_date',
    'format_number',
    'get_medal_icon',
    'format_table',
    'escape_html',
    'format_user_mention',
    'truncate',
    'format_list',
    'format_key_value'
]