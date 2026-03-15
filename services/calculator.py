"""
Расчеты зарплат и звезд (улучшенная версия)
"""

from typing import Dict, Any, List, Optional, Tuple
from database.db import get_all_zam_salaries, get_report_settings
from datetime import datetime, timedelta
import asyncio
import logging
from services.formatter import format_number

logger = logging.getLogger(__name__)

# Константы для расчета звезд
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

# Кэш для настроек
_settings_cache = None
_settings_cache_time = None
_settings_cache_lock = asyncio.Lock()


class SalaryCalculator:
    """Калькулятор зарплат с улучшенным кэшированием"""
    
    def __init__(self):
        self._local_cache = {}
        self.norm = 5
        self.bonus_percentage = 50
        self.salaries = {}
    
    async def _load_settings(self) -> Dict:
        """Загружает настройки из БД с блокировкой"""
        global _settings_cache, _settings_cache_time
        
        async with _settings_cache_lock:
            now = datetime.now()
            
            # Проверяем глобальный кэш
            if _settings_cache and _settings_cache_time:
                if (now - _settings_cache_time) < timedelta(minutes=5):
                    return _settings_cache
            
            # Загружаем свежие данные
            norm, bonus, _ = await get_report_settings()
            salaries = await get_all_zam_salaries()
            
            _settings_cache = {
                'norm': norm,
                'bonus_percentage': bonus,
                'salaries': salaries,
                'loaded_at': now.isoformat()
            }
            _settings_cache_time = now
            
            logger.debug(f"Settings loaded: norm={norm}, bonus={bonus}%")
            return _settings_cache
    
    async def load_settings(self, force: bool = False):
        """Загружает настройки с кэшированием"""
        cache = await self._load_settings()
        self.norm = cache['norm']
        self.bonus_percentage = cache['bonus_percentage']
        self.salaries = cache['salaries']
    
    def get_salary_for_level(self, level: int) -> int:
        """Получает зарплату для уровня"""
        return self.salaries.get(level, DEFAULT_SALARIES.get(level, 300000))
    
    async def calculate(self, zam_level: int, invites: int) -> Dict[str, Any]:
        """Рассчитывает данные отчета"""
        await self.load_settings()
        return self._calculate_sync(zam_level, invites)
    
    def _calculate_sync(self, zam_level: int, invites: int) -> Dict[str, Any]:
        """Синхронный расчет (без загрузки настроек)"""
        salary_per_person = self.get_salary_for_level(zam_level)
        bonus_salary_per_person = salary_per_person + (
            salary_per_person * self.bonus_percentage // 100
        )
        
        if invites >= self.norm:
            salary_for_norm = salary_per_person * self.norm
            extra_invites = invites - self.norm
            bonus_salary = extra_invites * bonus_salary_per_person
            norm_done = "✅ Выполнена"
        else:
            salary_for_norm = 0
            extra_invites = 0
            bonus_salary = 0
            norm_done = "❌ Не выполнена"
        
        total_salary = salary_for_norm + bonus_salary
        total_stars = self.calculate_stars(invites)
        
        return {
            'norm': self.norm,
            'norm_done': norm_done,
            'salary_per_person': salary_per_person,
            'bonus_salary_per_person': bonus_salary_per_person,
            'salary_for_norm': salary_for_norm,
            'extra_invites': extra_invites,
            'bonus_salary': bonus_salary,
            'total_salary': total_salary,
            'total_stars': total_stars,
            'bonus_percentage': self.bonus_percentage
        }
    
    async def calculate_many(self, reports_data: List[Tuple[int, int]]) -> List[Dict]:
        """Рассчитывает данные для нескольких отчетов (пакетно)"""
        await self.load_settings()
        return [self._calculate_sync(level, inv) for level, inv in reports_data]
    
    def calculate_stars(self, invites: int) -> int:
        """Рассчитывает звезды по формуле"""
        for threshold, stars in STARS_TABLE:
            if invites >= threshold:
                return stars
        return -1
    
    def calculate_required_invites(self, target_stars: int) -> int:
        """Рассчитывает необходимое количество инвайтов для получения звезд"""
        for threshold, stars in STARS_TABLE:
            if stars <= target_stars:
                return threshold
        return 0
    
    def get_stars_progress(self, invites: int) -> Dict[str, Any]:
        """Возвращает прогресс до следующих звезд"""
        current_stars = self.calculate_stars(invites)
        next_threshold = None
        next_stars = None
        
        for threshold, stars in sorted(STARS_TABLE, reverse=True):
            if stars < current_stars:
                next_threshold = threshold
                next_stars = stars
                break
        
        if next_threshold and next_stars:
            progress = invites / next_threshold * 100
            remaining = next_threshold - invites
            return {
                'current_stars': current_stars,
                'next_stars': next_stars,
                'next_threshold': next_threshold,
                'progress': progress,
                'remaining': remaining
            }
        
        return {'current_stars': current_stars, 'is_max': True}
    
    def format_salary_breakdown(self, zam_level: int, invites: int) -> str:
        """Форматирует детальный расчет зарплаты"""
        calc = self._calculate_sync(zam_level, invites)
        
        from utils.constants import STYLES
        
        lines = [
            f"📊 <b>Детальный расчет:</b>",
            f"   👤 Уровень зама: {zam_level}",
            f"   💰 Ставка за человека: {format_number(calc['salary_per_person'])}",
            f"   📈 Норма: {calc['norm']} чел.",
            f"   {calc['norm_done']}"
        ]
        
        if calc['salary_for_norm'] > 0:
            lines.append(f"   💵 За норму: {format_number(calc['salary_for_norm'])}")
        
        if calc['extra_invites'] > 0:
            lines.extend([
                f"   ➕ Сверх нормы: {calc['extra_invites']} чел.",
                f"   💰 Бонусная ставка: {format_number(calc['bonus_salary_per_person'])}",
                f"   ✨ Бонус: {format_number(calc['bonus_salary'])} ({calc['bonus_percentage']}%)"
            ])
        
        lines.append(f"   {STYLES['money']} <b>ИТОГО:</b> {format_number(calc['total_salary'])}")
        
        return "\n".join(lines)


# Создаем глобальный экземпляр для переиспользования
_calculator_instance = None


def get_calculator() -> SalaryCalculator:
    """Возвращает синглтон калькулятора"""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = SalaryCalculator()
    return _calculator_instance