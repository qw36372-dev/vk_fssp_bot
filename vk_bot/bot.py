"""
vk_bot/bot.py — Асинхронный HTTP-клиент для VK Teams Bot API.
Все методы API реализованы с retry-логикой и обработкой ошибок.
"""
import json
import logging
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Максимальное число попыток при ошибке сети
MAX_RETRIES = 3
RETRY_DELAY = 2.0
POLL_TIME = 25  # секунд для long-polling


class VKBot:
    """
    Клиент VK Teams Bot API.
    
    Базовый URL настраивается для VK Workspace (своя установка) или
    стандартного VK Teams (myteam.mail.ru).
    """

    def __init__(self, token: str, api_url: str = "https://myteam.mail.ru/bot/v1"):
        self.token = token
        self.api_url = api_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    async def start(self):
        """Создаём HTTP-сессию."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("✅ HTTP-сессия VK Bot создана")

    async def stop(self):
        """Закрываем HTTP-сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("✅ HTTP-сессия VK Bot закрыта")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    async def _get(self, method: str, params: Dict[str, Any]) -> Optional[Dict]:
        """GET-запрос к API."""
        params["token"] = self.token
        url = f"{self.api_url}/{method}"
        
        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(url, params=params) as resp:
                    data = await resp.json(content_type=None)
                    if not data.get("ok", False):
                        logger.warning(f"⚠️ API error [{method}]: {data}")
                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"⚠️ Network error [{method}] attempt {attempt+1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        return None

    async def _post_multipart(
        self, method: str, params: Dict[str, Any],
        file_bytes: bytes, filename: str
    ) -> Optional[Dict]:
        """POST multipart/form-data (для отправки файлов)."""
        params["token"] = self.token
        url = f"{self.api_url}/{method}"
        
        for attempt in range(MAX_RETRIES):
            try:
                form = aiohttp.FormData()
                for k, v in params.items():
                    form.add_field(k, str(v))
                form.add_field("file", file_bytes, filename=filename,
                               content_type="application/octet-stream")
                
                async with self._session.post(url, data=form) as resp:
                    raw = await resp.text()
                    if not raw or not raw.strip():
                        logger.info(f"✅ [{method}] пустой ответ (файл отправлен)")
                        return {"ok": True}
                    try:
                        import json as _json
                        data = _json.loads(raw)
                    except Exception:
                        logger.warning(f"⚠️ [{method}] не-JSON ответ: {raw[:200]}")
                        return {"ok": True, "raw": raw}
                    if not data.get("ok", False):
                        logger.warning(f"⚠️ API error [{method}]: {data}")
                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"⚠️ Network error [{method}] attempt {attempt+1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        return None

    # ------------------------------------------------------------------ #
    # Events (polling)
    # ------------------------------------------------------------------ #
    async def get_events(self, last_event_id: int = 0) -> Optional[Dict]:
        """Получить новые события (long-polling)."""
        return await self._get("events/get", {
            "lastEventId": last_event_id,
            "pollTime": POLL_TIME
        })

    # ------------------------------------------------------------------ #
    # Sending messages
    # ------------------------------------------------------------------ #
    async def send_text(
        self,
        chat_id: str,
        text: str,
        inline_keyboard: Optional[List[List[Dict]]] = None,
        parse_mode: str = "HTML"
    ) -> Optional[Dict]:
        """Отправить текстовое сообщение."""
        params: Dict[str, Any] = {
            "chatId": chat_id,
            "text": text,
            "parseMode": parse_mode
        }
        if inline_keyboard is not None:
            params["inlineKeyboardMarkup"] = json.dumps(inline_keyboard)
        return await self._get("messages/sendText", params)

    async def edit_text(
        self,
        chat_id: str,
        msg_id: str,
        text: str,
        inline_keyboard: Optional[List[List[Dict]]] = None,
        parse_mode: str = "HTML"
    ) -> Optional[Dict]:
        """Редактировать текст сообщения."""
        params: Dict[str, Any] = {
            "chatId": chat_id,
            "msgId": msg_id,
            "text": text,
            "parseMode": parse_mode
        }
        if inline_keyboard is not None:
            params["inlineKeyboardMarkup"] = json.dumps(inline_keyboard)
        return await self._get("messages/editText", params)

    async def delete_message(self, chat_id: str, msg_id: str) -> Optional[Dict]:
        """Удалить сообщение."""
        return await self._get("messages/deleteMessages", {
            "chatId": chat_id,
            "msgId": msg_id
        })

    async def answer_callback(
        self,
        query_id: str,
        text: str = "",
        show_alert: bool = False
    ) -> Optional[Dict]:
        """Ответить на callback-запрос (убрать часики)."""
        params: Dict[str, Any] = {"queryId": query_id}
        if text:
            params["text"] = text
            params["showAlert"] = "true" if show_alert else "false"
        return await self._get("messages/answerCallbackQuery", params)

    async def send_file(
        self,
        chat_id: str,
        file_bytes: bytes,
        filename: str,
        caption: str = ""
    ) -> Optional[Dict]:
        """Отправить файл (PDF, изображение и т.д.)."""
        params: Dict[str, Any] = {"chatId": chat_id}
        if caption:
            params["caption"] = caption
        return await self._post_multipart(
            "files/sendFile", params, file_bytes, filename
        )

    # ------------------------------------------------------------------ #
    # Self-info
    # ------------------------------------------------------------------ #
    async def self_get(self) -> Optional[Dict]:
        """Получить информацию о боте."""
        return await self._get("self/get", {})
