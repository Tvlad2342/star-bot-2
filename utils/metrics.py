"""
Простой сборщик статистики
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List


class SimpleMetrics:
    """Простой сборщик метрик"""
    
    def __init__(self):
        self.commands = Counter()
        self.commands_by_hour = defaultdict(lambda: Counter())
        self.errors = []
        self.start_time = datetime.now()
    
    def add_command(self, command: str):
        """Добавляет команду в статистику"""
        self.commands[command] += 1
        
        # Почасовая статистика
        hour = datetime.now().strftime("%Y-%m-%d %H:00")
        self.commands_by_hour[hour][command] += 1
    
    def add_error(self, error: str):
        """Добавляет ошибку"""
        self.errors.append({
            "time": datetime.now(),
            "error": error
        })
        # Оставляем только последние 50 ошибок
        if len(self.errors) > 50:
            self.errors = self.errors[-50:]
    
    def get_stats(self) -> Dict:
        """Возвращает статистику"""
        uptime = datetime.now() - self.start_time
        
        # Команды за последний час
        last_hour = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:00")
        commands_last_hour = sum(self.commands_by_hour[last_hour].values())
        
        return {
            "uptime": str(uptime).split('.')[0],
            "commands_total": sum(self.commands.values()),
            "commands_today": commands_last_hour,  # За последний час для простоты
            "errors_last_hour": len([
                e for e in self.errors 
                if e["time"] > datetime.now() - timedelta(hours=1)
            ]),
            "top_commands": dict(self.commands.most_common(5))
        }


metrics = SimpleMetrics()