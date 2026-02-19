"""
library/question_loader.py — Загрузка вопросов из JSON.
Поддержка вложенных папок + fallback на общий файл.
"""
import json
import logging
import random
from pathlib import Path
from typing import List

from config.settings import settings
from .models import Question
from .enum import Difficulty

logger = logging.getLogger(__name__)

DIFFICULTY_MAP = {
    "резерв": "reserve",
    "базовый": "basic",
    "стандартный": "standard",
    "продвинутый": "advanced"
}


def load_questions_for_specialization(
    specialization: str,
    difficulty: Difficulty,
    user_id: str | None = None
) -> List[Question]:
    """
    Загружает и перемешивает вопросы для специализации/уровня.
    
    Приоритет путей:
    1. questions/{specialization}/{difficulty}.json
    2. questions/{specialization}_{difficulty}.json
    3. questions/{specialization}.json (fallback)
    """
    difficulty_name = DIFFICULTY_MAP.get(difficulty.value, "basic")
    
    nested_path = settings.questions_dir / specialization / f"{difficulty_name}.json"
    flat_path = settings.questions_dir / f"{specialization}_{difficulty_name}.json"
    general_path = settings.questions_dir / f"{specialization}.json"
    
    if nested_path.exists():
        json_path = nested_path
        logger.info(f"📂 {specialization}/{difficulty_name}.json")
    elif flat_path.exists():
        json_path = flat_path
        logger.info(f"📂 {specialization}_{difficulty_name}.json")
    elif general_path.exists():
        json_path = general_path
        logger.warning(f"📂 Fallback: {specialization}.json")
    else:
        logger.error(f"❌ Файл вопросов не найден: {specialization} ({difficulty_name})")
        return []
    
    try:
        with json_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except (json.JSONDecodeError, PermissionError, OSError) as e:
        logger.error(f"❌ Ошибка чтения {json_path}: {e}")
        return []
    
    if not isinstance(raw_data, list):
        logger.error(f"❌ Неверный формат JSON {json_path}: ожидается список")
        return []
    
    questions = []
    for idx, item in enumerate(raw_data):
        try:
            opts = item.get("options", [])
            if not isinstance(opts, list) or len(opts) < 3:
                continue
            
            correct_str = str(item.get("correct_answers", ""))
            correct = set()
            for x in correct_str.split(","):
                x = x.strip()
                if x.isdigit():
                    correct.add(int(x))
            
            if not correct:
                continue
            
            q = Question(
                question=item["question"],
                options=opts,
                correct_answers=correct,
                difficulty=difficulty
            )
            q.shuffle_options()
            questions.append(q)
            
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"⚠️ Пропуск вопроса {specialization}:{idx}: {e}")
            continue
    
    if not questions:
        logger.error(f"❌ Нет валидных вопросов для {specialization}")
        return []
    
    target_count = settings.difficulty_questions.get(difficulty.value, 30)
    
    if user_id:
        try:
            random.seed(int(user_id))
        except (ValueError, TypeError):
            pass
    random.shuffle(questions)
    random.seed()
    
    if len(questions) < target_count:
        logger.warning(
            f"⚠️ Мало вопросов {specialization}: {len(questions)} < {target_count}"
        )
        selected = questions
    else:
        selected = questions[:target_count]
    
    logger.info(f"✅ Загружено {len(selected)} вопросов для {specialization} ({difficulty.value})")
    return selected
