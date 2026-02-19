"""
library/state_manager.py — In-memory FSM для VK Teams бота.
Заменяет aiogram FSMContext. Thread-safe через asyncio.Lock.
"""
import logging
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)


class UserState:
    """Состояние одного пользователя."""
    
    def __init__(self):
        self.state: Optional[str] = None
        self.data: Dict[str, Any] = {}


class StateManager:
    """
    Хранилище FSM-состояний всех пользователей в памяти.
    
    Ключ — user_id (строка). При перезапуске бота состояния сбрасываются.
    Для production можно заменить хранилище на Redis.
    """
    
    def __init__(self):
        self._store: Dict[str, UserState] = {}
        self._lock = asyncio.Lock()
    
    def _get_or_create(self, user_id: str) -> UserState:
        if user_id not in self._store:
            self._store[user_id] = UserState()
        return self._store[user_id]
    
    async def get_state(self, user_id: str) -> Optional[str]:
        """Получить текущее состояние пользователя."""
        async with self._lock:
            return self._store.get(user_id, UserState()).state
    
    async def set_state(self, user_id: str, state: Optional[str]) -> None:
        """Установить состояние пользователя."""
        async with self._lock:
            self._get_or_create(user_id).state = state
    
    async def get_data(self, user_id: str) -> Dict[str, Any]:
        """Получить все данные пользователя."""
        async with self._lock:
            return dict(self._store.get(user_id, UserState()).data)
    
    async def update_data(self, user_id: str, **kwargs) -> None:
        """Обновить данные пользователя (merge, не replace)."""
        async with self._lock:
            self._get_or_create(user_id).data.update(kwargs)
    
    async def clear(self, user_id: str) -> None:
        """Очистить состояние и данные пользователя."""
        async with self._lock:
            if user_id in self._store:
                del self._store[user_id]
    
    def user_count(self) -> int:
        """Количество пользователей с активным состоянием."""
        return len(self._store)


# Глобальный экземпляр
state_manager = StateManager()
