"""
vk_bot/types.py — Типы данных VK Teams Bot API.
Оборачивают raw JSON payload в удобные объекты.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class VKUser:
    userId: str
    firstName: str = ""
    lastName: str = ""
    nick: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.firstName} {self.lastName}".strip() or self.userId


@dataclass
class VKChat:
    chatId: str
    type: str = "private"  # private, group, channel
    title: str = ""


@dataclass
class VKMessage:
    msgId: str
    chat: VKChat
    from_user: VKUser
    text: str = ""
    timestamp: int = 0


@dataclass
class VKCallbackQuery:
    queryId: str
    from_user: VKUser
    message: VKMessage
    callbackData: str = ""


@dataclass
class VKEvent:
    """Событие от VK Teams API."""
    type: str
    payload: Dict[str, Any]
    event_id: int = 0

    @property
    def message(self) -> Optional[VKMessage]:
        if self.type not in ("newMessage", "editedMessage"):
            return None
        p = self.payload
        chat_data = p.get("chat", {})
        from_data = p.get("from", {})
        return VKMessage(
            msgId=str(p.get("msgId", "")),
            chat=VKChat(
                chatId=str(chat_data.get("chatId", "")),
                type=chat_data.get("type", "private"),
                title=chat_data.get("title", "")
            ),
            from_user=VKUser(
                userId=str(from_data.get("userId", "")),
                firstName=from_data.get("firstName", ""),
                lastName=from_data.get("lastName", ""),
                nick=from_data.get("nick", "")
            ),
            text=p.get("text", ""),
            timestamp=p.get("timestamp", 0)
        )

    @property
    def callback_query(self) -> Optional[VKCallbackQuery]:
        if self.type != "callbackQuery":
            return None
        p = self.payload
        from_data = p.get("from", {})
        msg_data = p.get("message", {})
        msg_chat = msg_data.get("chat", {})
        msg_from = msg_data.get("from", {})
        return VKCallbackQuery(
            queryId=str(p.get("queryId", "")),
            from_user=VKUser(
                userId=str(from_data.get("userId", "")),
                firstName=from_data.get("firstName", ""),
                lastName=from_data.get("lastName", ""),
                nick=from_data.get("nick", "")
            ),
            message=VKMessage(
                msgId=str(msg_data.get("msgId", "")),
                chat=VKChat(
                    chatId=str(msg_chat.get("chatId", "")),
                    type=msg_chat.get("type", "private")
                ),
                from_user=VKUser(userId=str(msg_from.get("userId", ""))),
                text=msg_data.get("text", "")
            ),
            callbackData=p.get("callbackData", "")
        )


# Типы кнопок VK Teams
STYLE_PRIMARY = "primary"
STYLE_BASE = "base"
STYLE_ATTENTION = "attention"
