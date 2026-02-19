"""
library/models.py — Модели Question и CurrentTestState.
Идентичны Telegram-версии, без изменений.
"""
import time
import random
from typing import List, Set, Optional, Dict
from pydantic import BaseModel, Field, field_validator

from .enum import Difficulty


class Question(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    options: List[str] = Field(..., min_length=3, max_length=6)
    correct_answers: Set[int] = Field(..., min_length=1)
    difficulty: Difficulty = Difficulty.BASIC
    original_options: Optional[List[str]] = None
    shuffle_mapping: Optional[List[int]] = None

    @field_validator('correct_answers', mode='after')
    @classmethod
    def validate_correct(cls, v, info):
        options = info.data.get('options', [])
        max_opt = len(options)
        if any(i < 1 or i > max_opt for i in v):
            raise ValueError(f'correct_answers: индексы должны быть в диапазоне 1..{max_opt}')
        return v

    def shuffle_options(self) -> None:
        if self.original_options is None:
            self.original_options = self.options.copy()
        indices = list(range(len(self.options)))
        random.shuffle(indices)
        self.shuffle_mapping = indices
        shuffled_options = [self.options[i] for i in indices]
        old_to_new = {old: new for new, old in enumerate(indices)}
        new_correct = {old_to_new[c - 1] + 1 for c in self.correct_answers}
        self.options = shuffled_options
        self.correct_answers = new_correct


class CurrentTestState(BaseModel):
    questions: List[Question]
    current_index: int = 0
    selected_answers: Set[int] = Field(default_factory=set)
    answers_history: Dict[int, Set[int]] = Field(default_factory=dict)
    start_time: float = Field(default_factory=time.time)
    timer_task: Optional[object] = None
    last_message_id: Optional[str] = None  # str в VK Teams (msgId)

    # Данные пользователя
    full_name: str = ""
    position: str = ""
    department: str = ""
    specialization: str = ""
    difficulty: Difficulty = Difficulty.BASIC

    # Результаты
    correct_count: int = 0
    total_questions: int = 0
    percentage: float = 0.0
    grade: str = ""
    elapsed_time: str = ""

    model_config = {"arbitrary_types_allowed": True}

    def save_answer(self, question_index: int) -> None:
        self.answers_history[question_index] = self.selected_answers.copy()

    def load_answer(self, question_index: int) -> None:
        if question_index in self.answers_history:
            self.selected_answers = self.answers_history[question_index].copy()
        else:
            self.selected_answers = set()

    def calculate_results(self) -> None:
        self.total_questions = len(self.questions)
        self.correct_count = 0
        for idx, question in enumerate(self.questions):
            user_answer = self.answers_history.get(idx, set())
            if user_answer == question.correct_answers:
                self.correct_count += 1
        self.percentage = (
            (self.correct_count / self.total_questions) * 100
            if self.total_questions > 0 else 0.0
        )
        if self.percentage >= 90:
            self.grade = "отлично"
        elif self.percentage >= 75:
            self.grade = "хорошо"
        elif self.percentage >= 60:
            self.grade = "удовлетворительно"
        else:
            self.grade = "неудовлетворительно"
        elapsed = time.time() - self.start_time
        self.elapsed_time = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
