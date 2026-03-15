"""
Модуль для базовой трассировки запросов
"""

import time
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional

# Контекст для хранения времени начала запроса
_request_start: ContextVar[Optional[float]] = ContextVar('request_start', default=None)
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def generate_request_id() -> str:
    """Генерирует ID запроса"""
    return uuid.uuid4().hex[:6]


@contextmanager
def track_request():
    """Отслеживает время выполнения запроса"""
    request_id = generate_request_id()
    start_time = time.time()
    
    token_id = _request_id.set(request_id)
    token_time = _request_start.set(start_time)
    
    try:
        yield
    finally:
        _request_id.reset(token_id)
        _request_start.reset(token_time)


def get_request_id() -> Optional[str]:
    """Возвращает ID текущего запроса"""
    return _request_id.get()


def get_request_duration() -> Optional[float]:
    """Возвращает длительность текущего запроса"""
    start = _request_start.get()
    if start:
        return (time.time() - start) * 1000
    return None


def get_trace_info() -> Optional[dict]:
    """Возвращает информацию о текущей трассировке"""
    request_id = get_request_id()
    duration = get_request_duration()
    
    if request_id and duration:
        return {
            "trace_id": request_id,
            "duration_ms": round(duration, 2)
        }
    return None


def format_trace() -> str:
    """Форматирует информацию о трассировке для вывода"""
    info = get_trace_info()
    if info:
        return f"[{info['trace_id']}] {info['duration_ms']}ms"
    return ""


class TraceMiddleware:
    """Middleware для отслеживания времени запросов"""
    
    async def __call__(self, handler, event, data):
        with track_request():
            return await handler(event, data)