"""
config/settings.py — Конфигурация VK Workspace бота.
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # === КРИТИЧЕСКИЕ ПАРАМЕТРЫ ===
    # Токен бота (из Metabot в VK Teams)
    api_token: str = Field(default="")
    # URL API: для стандартного VK Teams — https://myteam.mail.ru/bot/v1
    # Для корпоративного VK Workspace — URL вашего сервера
    api_url: str = Field(default="https://myteam.mail.ru/bot/v1")
    environment: str = Field(default="production")

    # === ПУТИ ===
    base_dir: Path = Path(__file__).parent.parent
    questions_dir: Path = base_dir / "questions"
    data_dir:      Path = base_dir / "data"
    logs_dir:      Path = base_dir / "logs"

    # === ТАЙМИНГИ УРОВНЕЙ СЛОЖНОСТИ (минуты) ===
    difficulty_times: Dict[str, int] = {
        "резерв":       35,
        "базовый":      25,
        "стандартный":  20,
        "продвинутый":  20,
    }

    # === КОЛИЧЕСТВО ВОПРОСОВ ===
    difficulty_questions: Dict[str, int] = {
        "резерв":       20,
        "базовый":      30,
        "стандартный":  40,
        "продвинутый":  50,
    }

    # === СПЕЦИАЛИЗАЦИИ ===
    specializations: list[str] = [
        "oupds", "ispolniteli", "aliment", "doznanie", "rozyisk",
        "prof", "oko", "informatika", "kadry", "bezopasnost", "upravlenie"
    ]

    answers_show_time: int = 60   # секунд до удаления ответов
    log_level: str = "INFO"
    use_file_logging: bool = True

    model_config = {"case_sensitive": False}

    @field_validator("api_token", mode="before")
    @classmethod
    def validate_api_token(cls, v):
        token = v or os.getenv("API_TOKEN", "").strip()
        if not token:
            print("❌ API_TOKEN не установлен!", file=sys.stderr)
        return token

    @field_validator("api_url", mode="before")
    @classmethod
    def validate_api_url(cls, v):
        return v or os.getenv("API_URL", "https://myteam.mail.ru/bot/v1").strip()

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        return (v or os.getenv("ENVIRONMENT", "production")).lower()


settings = Settings()
logger = logging.getLogger(__name__)


def setup_logging():
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    if settings.use_file_logging:
        try:
            settings.logs_dir.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(settings.logs_dir / "bot.log", encoding="utf-8")
            fh.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            logging.getLogger().addHandler(fh)
        except OSError as e:
            logger.warning(f"⚠️ Файловое логирование недоступно: {e}")


def ensure_dirs():
    for d in [settings.data_dir, settings.logs_dir, settings.questions_dir]:
        d.mkdir(parents=True, exist_ok=True)


setup_logging()
ensure_dirs()
