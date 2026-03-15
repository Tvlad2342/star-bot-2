"""
Работа с базой данных (оптимизированная версия)
"""

import aiosqlite
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any, AsyncIterator
from config import DATABASE_PATH
from database.models import User, Task, Report

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Единое подключение к БД с автоматическим закрытием"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
        await db.commit()


# ========== ИНИЦИАЛИЗАЦИЯ БД ==========

async def init_db():
    """Создает все таблицы в базе данных"""
    async with get_db() as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                stars INTEGER DEFAULT 0,
                role INTEGER DEFAULT 0
            )
        """)
        
        # Таблица истории
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issuer_id INTEGER,
                target_id INTEGER,
                amount INTEGER,
                action TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица снимков звезд (для топа)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS star_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stars INTEGER,
                snapshot_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Таблица ников
        await db.execute("""
            CREATE TABLE IF NOT EXISTS nicknames (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Таблица настроек отчетов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS report_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                norm INTEGER DEFAULT 5,
                bonus_percentage INTEGER DEFAULT 50,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Вставляем начальные настройки, если их нет
        await db.execute("""
            INSERT OR IGNORE INTO report_settings (id, norm, bonus_percentage)
            VALUES (1, 5, 50)
        """)
        
        # Таблица зарплат по уровням
        await db.execute("""
            CREATE TABLE IF NOT EXISTS zam_levels (
                level INTEGER PRIMARY KEY,
                salary INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Вставляем начальные зарплаты, если их нет
        default_salaries = [
            (1, 300000),
            (2, 400000),
            (3, 500000),
            (4, 600000),
            (5, 700000)
        ]
        for level, salary in default_salaries:
            await db.execute("""
                INSERT OR IGNORE INTO zam_levels (level, salary)
                VALUES (?, ?)
            """, (level, salary))
        
        # Таблица отчетов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE NOT NULL,
                zam_id INTEGER NOT NULL,
                invites_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (zam_id) REFERENCES users (id)
            )
        """)
        
        # Таблица задач
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_number INTEGER NOT NULL UNIQUE,
                description TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',
                completed_by INTEGER,
                completed_at TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (completed_by) REFERENCES users(id)
            )
        """)
        
        # Таблица истории задач
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                action TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Таблица для отслеживания отправленных уведомлений о задачах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL, -- 'upcoming' or 'overdue'
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)


async def init_db_with_indexes():
    """Создает все таблицы и индексы"""
    await init_db()
    async with get_db() as db:
        # Дополнительные индексы
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_user_date ON star_snapshots(user_id, snapshot_date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_stars ON users(stars)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_notifications_task ON task_notifications(task_id)")
        
        logger.info("База данных инициализирована с индексами")


# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========

async def get_or_create_user(user_id: int, username: str) -> User:
    """Быстрое получение или создание пользователя"""
    async with get_db() as db:
        async with db.execute("""
            SELECT u.id, u.username, u.stars, u.role, n.nickname
            FROM users u
            LEFT JOIN nicknames n ON u.id = n.user_id
            WHERE u.id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                stars=row['stars'],
                role=row['role'],
                nickname=row['nickname']
            )
        
        await db.execute(
            "INSERT INTO users (id, username, stars, role) VALUES (?, ?, 0, 0)",
            (user_id, username)
        )
        
        return User(
            id=user_id,
            username=username,
            stars=0,
            role=0,
            nickname=None
        )


async def get_user_by_id(user_id: int) -> Optional[User]:
    """Получение пользователя по ID"""
    async with get_db() as db:
        async with db.execute("""
            SELECT u.id, u.username, u.stars, u.role, n.nickname
            FROM users u
            LEFT JOIN nicknames n ON u.id = n.user_id
            WHERE u.id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        return User(
            id=row['id'],
            username=row['username'],
            stars=row['stars'],
            role=row['role'],
            nickname=row['nickname']
        )


async def get_user_by_username(username: str) -> Optional[User]:
    """Получение пользователя по юзернейму"""
    async with get_db() as db:
        async with db.execute("""
            SELECT u.id, u.username, u.stars, u.role, n.nickname
            FROM users u
            LEFT JOIN nicknames n ON u.id = n.user_id
            WHERE u.username = ?
        """, (username,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        return User(
            id=row['id'],
            username=row['username'],
            stars=row['stars'],
            role=row['role'],
            nickname=row['nickname']
        )


async def get_all_users() -> List[User]:
    """Получает всех пользователей"""
    async with get_db() as db:
        async with db.execute("""
            SELECT u.id, u.username, u.stars, u.role, n.nickname
            FROM users u
            LEFT JOIN nicknames n ON u.id = n.user_id
            ORDER BY u.stars DESC
        """) as cursor:
            rows = await cursor.fetchall()
        
        return [
            User(
                id=row['id'],
                username=row['username'],
                stars=row['stars'],
                role=row['role'],
                nickname=row['nickname']
            ) for row in rows
        ]


async def update_user_stars(user_id: int, stars: int):
    """Обновляет количество звезд"""
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET stars = ? WHERE id = ?",
            (stars, user_id)
        )


async def update_user_role(user_id: int, role: int):
    """Обновляет роль пользователя"""
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id)
        )


async def delete_user(user_id: int):
    """Удаляет пользователя"""
    async with get_db() as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ========== РАБОТА С НИКАМИ ==========

async def set_nickname(user_id: int, nickname: str):
    """Устанавливает ник"""
    async with get_db() as db:
        await db.execute("""
            INSERT OR REPLACE INTO nicknames (user_id, nickname) 
            VALUES (?, ?)
        """, (user_id, nickname))


async def get_nickname(user_id: int) -> Optional[str]:
    """Получает ник"""
    async with get_db() as db:
        async with db.execute(
            "SELECT nickname FROM nicknames WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result['nickname'] if result else None


async def delete_nickname(user_id: int):
    """Удаляет ник"""
    async with get_db() as db:
        await db.execute("DELETE FROM nicknames WHERE user_id = ?", (user_id,))


async def get_all_nicknames() -> List[Tuple[int, str, str]]:
    """Получает все ники"""
    async with get_db() as db:
        async with db.execute("""
            SELECT u.id, u.username, n.nickname 
            FROM users u
            LEFT JOIN nicknames n ON u.id = n.user_id
            WHERE n.nickname IS NOT NULL
            ORDER BY n.nickname
        """) as cursor:
            rows = await cursor.fetchall()
            return [(row['id'], row['username'], row['nickname']) for row in rows]


# ========== РАБОТА С ИСТОРИЕЙ ==========

async def add_history(issuer_id: int, target_id: int, amount: int, action: str):
    """Добавляет запись в историю"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO history (issuer_id, target_id, amount, action) VALUES (?, ?, ?, ?)",
            (issuer_id, target_id, amount, action)
        )


async def get_user_history(user_id: int, limit: int = 15) -> List[Tuple]:
    """Получает историю пользователя"""
    async with get_db() as db:
        async with db.execute("""
            SELECT h.issuer_id, u.username, h.amount, h.action, h.timestamp
            FROM history h
            LEFT JOIN users u ON h.issuer_id = u.id
            WHERE h.target_id = ?
            ORDER BY h.timestamp DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [(row['issuer_id'], row['username'], row['amount'], 
                    row['action'], row['timestamp']) for row in rows]


async def get_all_history(limit: int = 30) -> List[Tuple]:
    """Получает всю историю изменений"""
    async with get_db() as db:
        async with db.execute("""
            SELECT 
                h.issuer_id, 
                COALESCE(issuer_u.username, 'Неизвестно') as issuer_name,
                h.target_id, 
                COALESCE(target_u.username, 'Неизвестно') as target_name,
                h.amount, 
                h.action, 
                h.timestamp
            FROM history h
            LEFT JOIN users issuer_u ON h.issuer_id = issuer_u.id
            LEFT JOIN users target_u ON h.target_id = target_u.id
            ORDER BY h.timestamp DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [(row['issuer_id'], row['issuer_name'], row['target_id'],
                    row['target_name'], row['amount'], row['action'], 
                    row['timestamp']) for row in rows]


# ========== РАБОТА СО ЗВЕЗДАМИ И ТОПАМИ ==========

async def create_star_snapshot(user_id: int, stars: int):
    """Создает снимок звезд"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO star_snapshots (user_id, stars) VALUES (?, ?)",
            (user_id, stars)
        )


async def get_top_by_period(days: int = 30, limit: int = 10, period_type: str = 'days') -> List[Tuple]:
    """
    Топ по приросту звезд за период
    period_type: 'days' - обычный период за последние N дней
                 'week' - календарная неделя (пн-вс)
                 'month' - календарный месяц
    """
    async with get_db() as db:
        now = datetime.now()
        period_text = ""
        
        if period_type == 'week':
            # Определяем начало текущей недели (понедельник)
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_of_week.strftime("%Y-%m-%d %H:%M:%S")
            
            # Конец недели (воскресенье)
            end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
            period_text = f"{start_of_week.strftime('%d.%m')} - {end_of_week.strftime('%d.%m')}"
            
        elif period_type == 'month':
            # Начало текущего месяца
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_date = start_of_month.strftime("%Y-%m-%d %H:%M:%S")
            
            # Название месяца на русском
            month_names = [
                "ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ",
                "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"
            ]
            period_text = month_names[now.month - 1]
            
        else:
            # Обычный период за последние N дней
            start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            period_text = f"последние {days} дней"
        
        query = """
            WITH current_data AS (
                SELECT u.id, u.username, u.stars as current_stars, u.role
                FROM users u
                WHERE u.stars > 0
            ),
            old_data AS (
                SELECT ss.user_id, ss.stars as old_stars
                FROM star_snapshots ss
                WHERE ss.snapshot_date >= ?
                GROUP BY ss.user_id
                HAVING MIN(ss.snapshot_date)
            )
            SELECT 
                cd.id,
                cd.username,
                cd.current_stars,
                COALESCE(od.old_stars, 0) as old_stars,
                (cd.current_stars - COALESCE(od.old_stars, 0)) as growth,
                cd.role
            FROM current_data cd
            LEFT JOIN old_data od ON cd.id = od.user_id
            WHERE (cd.current_stars - COALESCE(od.old_stars, 0)) > 0
            ORDER BY growth DESC
            LIMIT ?
        """
        async with db.execute(query, (start_date, limit)) as cursor:
            rows = await cursor.fetchall()
            return [(row['id'], row['username'], row['current_stars'],
                    row['old_stars'], row['growth'], row['role'], period_text) for row in rows]


async def get_top_overall(limit: int = 10) -> List[Tuple]:
    """Общий топ по звездам"""
    async with get_db() as db:
        async with db.execute("""
            SELECT id, username, stars, role
            FROM users
            WHERE stars > 0
            ORDER BY stars DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [(row['id'], row['username'], row['stars'], row['role']) for row in rows]


async def get_user_growth(user_id: int, days: int) -> int:
    """Рост звезд пользователя за период"""
    async with get_db() as db:
        # Текущие звезды
        async with db.execute(
            "SELECT stars FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            current = await cursor.fetchone()
            if not current:
                return 0
            current_stars = current['stars']
        
        # Старые звезды (самый старый снимок за период)
        async with db.execute("""
            SELECT stars FROM star_snapshots 
            WHERE user_id = ? AND snapshot_date >= datetime('now', ? || ' days')
            ORDER BY snapshot_date ASC
            LIMIT 1
        """, (user_id, str(days))) as cursor:
            old = await cursor.fetchone()
            old_stars = old['stars'] if old else current_stars
        
        return current_stars - old_stars


async def clear_top_data() -> int:
    """Очищает данные для топа и создает новые снимки"""
    async with get_db() as db:
        # Очищаем таблицу снимков
        await db.execute("DELETE FROM star_snapshots")
        
        # Получаем всех пользователей
        async with db.execute("SELECT id, stars FROM users") as cursor:
            users = await cursor.fetchall()
        
        # Создаем новые снимки
        for user in users:
            await db.execute(
                "INSERT INTO star_snapshots (user_id, stars) VALUES (?, ?)",
                (user['id'], user['stars'])
            )
        
        return len(users)


# ========== РАБОТА С ЗАДАЧАМИ И УВЕДОМЛЕНИЯМИ ==========

async def create_task(task_number: int, description: str, created_by: int, deadline: str) -> int:
    """Создает новую задачу"""
    async with get_db() as db:
        cursor = await db.execute("""
            INSERT INTO tasks (task_number, description, created_by, deadline)
            VALUES (?, ?, ?, ?)
        """, (task_number, description, created_by, deadline))
        task_id = cursor.lastrowid
        
        await db.execute("""
            INSERT INTO tasks_history (task_id, action, user_id, details)
            VALUES (?, 'add', ?, ?)
        """, (task_id, created_by, f"Создана задача #{task_number}"))
        
        return task_id


async def get_all_active_tasks() -> List[Task]:
    """Получает все активные задачи"""
    async with get_db() as db:
        async with db.execute("""
            SELECT t.*, 
                   creator.username as creator_name,
                   completer.username as completer_name
            FROM tasks t
            LEFT JOIN users creator ON t.created_by = creator.id
            LEFT JOIN users completer ON t.completed_by = completer.id
            WHERE t.status != 'completed'
            ORDER BY t.deadline ASC
        """) as cursor:
            rows = await cursor.fetchall()
        
        tasks = []
        for row in rows:
            tasks.append(Task(
                id=row['id'],
                task_number=row['task_number'],
                description=row['description'],
                created_by=row['created_by'],
                created_at=row['created_at'],
                deadline=row['deadline'],
                status=row['status'],
                completed_by=row['completed_by'],
                completed_at=row['completed_at'],
                creator_name=row['creator_name'],
                completer_name=row['completer_name']
            ))
        
        return tasks


async def get_task_by_number(task_number: int) -> Optional[Task]:
    """Получает задачу по номеру"""
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM tasks WHERE task_number = ? AND status != 'completed'
        """, (task_number,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        return Task(
            id=row['id'],
            task_number=row['task_number'],
            description=row['description'],
            created_by=row['created_by'],
            created_at=row['created_at'],
            deadline=row['deadline'],
            status=row['status'],
            completed_by=row['completed_by'],
            completed_at=row['completed_at']
        )


async def complete_task(task_number: int, user_id: int):
    """Отмечает задачу выполненной"""
    async with get_db() as db:
        await db.execute("""
            UPDATE tasks 
            SET status = 'completed', 
                completed_by = ?, 
                completed_at = CURRENT_TIMESTAMP
            WHERE task_number = ? AND status = 'pending'
        """, (user_id, task_number))
        
        await db.execute("""
            INSERT INTO tasks_history (task_id, action, user_id, details)
            SELECT id, 'complete', ?, 'Задача выполнена'
            FROM tasks WHERE task_number = ?
        """, (user_id, task_number))


async def delete_task(task_number: int, user_id: int):
    """Удаляет задачу"""
    async with get_db() as db:
        # Добавляем запись в историю
        await db.execute("""
            INSERT INTO tasks_history (task_id, action, user_id, details)
            SELECT id, 'delete', ?, 'Задача удалена'
            FROM tasks WHERE task_number = ?
        """, (user_id, task_number))
        
        # Удаляем задачу
        await db.execute("DELETE FROM tasks WHERE task_number = ?", (task_number,))


async def check_overdue_tasks() -> List[Task]:
    """Проверяет просроченные задачи"""
    async with get_db() as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with db.execute("""
            SELECT t.*, u.username
            FROM tasks t
            LEFT JOIN users u ON t.created_by = u.id
            WHERE t.status = 'pending' AND t.deadline < ?
        """, (now,)) as cursor:
            rows = await cursor.fetchall()
        
        tasks = []
        for row in rows:
            tasks.append(Task(
                id=row['id'],
                task_number=row['task_number'],
                description=row['description'],
                created_by=row['created_by'],
                created_at=row['created_at'],
                deadline=row['deadline'],
                status=row['status'],
                completed_by=row['completed_by'],
                completed_at=row['completed_at'],
                creator_name=row['username']
            ))
        
        return tasks


async def update_overdue_status():
    """Обновляет статус просроченных задач"""
    async with get_db() as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute("""
            UPDATE tasks 
            SET status = 'overdue' 
            WHERE status = 'pending' AND deadline < ?
        """, (now,))


async def check_upcoming_task_notification_sent(task_id: int) -> bool:
    """Проверяет, отправлялось ли уже уведомление о скором просрочке для задачи"""
    async with get_db() as db:
        async with db.execute("""
            SELECT id FROM task_notifications 
            WHERE task_id = ? AND notification_type = 'upcoming'
        """, (task_id,)) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def check_overdue_task_notification_sent(task_id: int) -> bool:
    """Проверяет, отправлялось ли уже уведомление о просрочке для задачи"""
    async with get_db() as db:
        async with db.execute("""
            SELECT id FROM task_notifications 
            WHERE task_id = ? AND notification_type = 'overdue'
        """, (task_id,)) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def mark_upcoming_notification_sent(task_id: int):
    """Отмечает, что уведомление о скором просрочке отправлено"""
    async with get_db() as db:
        await db.execute("""
            INSERT INTO task_notifications (task_id, notification_type)
            VALUES (?, 'upcoming')
        """, (task_id,))


async def mark_overdue_notification_sent(task_id: int):
    """Отмечает, что уведомление о просрочке отправлено"""
    async with get_db() as db:
        await db.execute("""
            INSERT INTO task_notifications (task_id, notification_type)
            VALUES (?, 'overdue')
        """, (task_id,))


# ========== РАБОТА С ОТЧЕТАМИ ==========

async def get_report_settings() -> Tuple[int, int, int]:
    """Получает настройки отчетов"""
    async with get_db() as db:
        async with db.execute(
            "SELECT norm, bonus_percentage FROM report_settings ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            return row['norm'], row['bonus_percentage'], 1
        
        return 5, 50, 1


async def update_report_norm(norm: int):
    """Обновляет норму"""
    async with get_db() as db:
        await db.execute("""
            UPDATE report_settings SET norm = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (norm,))


async def update_report_bonus(bonus: int):
    """Обновляет процент бонуса"""
    async with get_db() as db:
        await db.execute("""
            UPDATE report_settings SET bonus_percentage = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (bonus,))


async def set_zam_salary(level: int, salary: int):
    """Устанавливает зарплату для уровня"""
    async with get_db() as db:
        await db.execute("""
            INSERT OR REPLACE INTO zam_levels (level, salary, last_updated) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (level, salary))


async def get_all_zam_salaries() -> Dict[int, int]:
    """Получает все зарплаты"""
    async with get_db() as db:
        async with db.execute(
            "SELECT level, salary FROM zam_levels ORDER BY level"
        ) as cursor:
            rows = await cursor.fetchall()
            return {row['level']: row['salary'] for row in rows}


async def add_report(report_date: str, zam_id: int, invites: int):
    """Добавляет отчет"""
    async with get_db() as db:
        # Проверяем, есть ли уже отчет
        async with db.execute("""
            SELECT id FROM reports 
            WHERE report_date = ? AND zam_id = ?
        """, (report_date, zam_id)) as cursor:
            exists = await cursor.fetchone()
        
        if exists:
            await db.execute("""
                UPDATE reports SET invites_count = ? 
                WHERE report_date = ? AND zam_id = ?
            """, (invites, report_date, zam_id))
        else:
            await db.execute("""
                INSERT INTO reports (report_date, zam_id, invites_count) 
                VALUES (?, ?, ?)
            """, (report_date, zam_id, invites))


async def get_reports_by_date(report_date: str) -> List[Report]:
    """Получает отчеты за дату"""
    async with get_db() as db:
        async with db.execute("""
            SELECT r.*, u.username, n.nickname, u.role 
            FROM reports r
            LEFT JOIN users u ON r.zam_id = u.id
            LEFT JOIN nicknames n ON r.zam_id = n.user_id
            WHERE r.report_date = ?
            ORDER BY u.role DESC, r.invites_count DESC
        """, (report_date,)) as cursor:
            rows = await cursor.fetchall()
        
        reports = []
        for row in rows:
            reports.append(Report(
                id=row['id'],
                report_date=row['report_date'],
                zam_id=row['zam_id'],
                invites_count=row['invites_count'],
                username=row['username'],
                nickname=row['nickname'],
                zam_level=row['role']
            ))
        
        return reports


async def delete_reports_by_date(report_date: str):
    """Удаляет отчеты за дату"""
    async with get_db() as db:
        await db.execute("DELETE FROM reports WHERE report_date = ?", (report_date,))


async def get_reports_for_period(start_date: str, end_date: str) -> List[Report]:
    """Получает отчеты за период"""
    async with get_db() as db:
        async with db.execute("""
            SELECT r.*, u.username, n.nickname, u.role 
            FROM reports r
            LEFT JOIN users u ON r.zam_id = u.id
            LEFT JOIN nicknames n ON r.zam_id = n.user_id
            WHERE r.report_date BETWEEN ? AND ?
            ORDER BY r.report_date DESC, u.role DESC
        """, (start_date, end_date)) as cursor:
            rows = await cursor.fetchall()
        
        reports = []
        for row in rows:
            reports.append(Report(
                id=row['id'],
                report_date=row['report_date'],
                zam_id=row['zam_id'],
                invites_count=row['invites_count'],
                username=row['username'],
                nickname=row['nickname'],
                zam_level=row['role']
            ))
        
        return reports


# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ОТЧЕТОВ ==========

async def get_all_reports_dates(start_date: str, end_date: str) -> List[str]:
    """Получает все уникальные даты с отчетами за период"""
    async with get_db() as db:
        async with db.execute("""
            SELECT DISTINCT report_date
            FROM reports
            WHERE report_date BETWEEN ? AND ?
            ORDER BY report_date DESC
        """, (start_date, end_date)) as cursor:
            rows = await cursor.fetchall()
            return [row['report_date'] for row in rows]


async def get_all_reports_grouped_by_month() -> Dict[str, Dict]:
    """Получает все отчеты, сгруппированные по месяцам"""
    from collections import defaultdict
    import calendar
    
    async with get_db() as db:
        async with db.execute("""
            SELECT DISTINCT report_date
            FROM reports
            WHERE report_date >= '2026-01-01'
            ORDER BY report_date DESC
        """) as cursor:
            rows = await cursor.fetchall()
            
            if not rows:
                return {}
            
            months = defaultdict(list)
            for row in rows:
                date = row['report_date']
                year_month = date[:7]
                months[year_month].append(date)
            
            result = {}
            for year_month, dates in months.items():
                year, month = map(int, year_month.split('-'))
                
                month_names = [
                    "ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ",
                    "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"
                ]
                month_name = month_names[month - 1]
                
                last_day = calendar.monthrange(year, month)[1]
                date_range = f"01.{month:02d}.{str(year)[2:]} - {last_day:02d}.{month:02d}.{str(year)[2:]}"
                
                result[year_month] = {
                    'month_name': month_name,
                    'date_range': date_range,
                    'reports': sorted(dates)
                }
            
            return result


async def bulk_update_stars(updates: List[Tuple[int, int]]):
    """Массовое обновление звезд"""
    async with get_db() as db:
        async with db.execute("BEGIN TRANSACTION"):
            for user_id, stars in updates:
                await db.execute(
                    "UPDATE users SET stars = ? WHERE id = ?",
                    (stars, user_id)
                )