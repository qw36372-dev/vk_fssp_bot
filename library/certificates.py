"""
library/certificates.py — Генерация PDF сертификатов ФССП.
Корпоративный дизайн с официальным гербом.
"""
import io
import logging
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config.settings import settings
from .models import CurrentTestState

logger = logging.getLogger(__name__)

FONT_PATH   = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
EMBLEM_PATH = Path(__file__).parent / "static" / "fssp_emblem_opt.png"


def register_fonts() -> str:
    try:
        if FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_PATH)))
            return "DejaVu"
    except Exception as e:
        logger.error(f"❌ Ошибка шрифта: {e}")
    return "Helvetica"


def draw_decorative_border(c, width, height):
    c.setStrokeColor(colors.HexColor("#006400"))
    c.setLineWidth(3)
    c.rect(30, 30, width - 60, height - 60)

    c.setStrokeColor(colors.HexColor("#2e8b57"))
    c.setLineWidth(1.5)
    c.rect(40, 40, width - 80, height - 80)

    corner_size = 15
    c.setStrokeColor(colors.HexColor("#d4af37"))
    c.setLineWidth(2)
    for (x, y, dx, dy) in [
        (40, height - 40, corner_size, -corner_size),
        (width - 40, height - 40, -corner_size, -corner_size),
        (40, 40, corner_size, corner_size),
        (width - 40, 40, -corner_size, corner_size),
    ]:
        c.line(x, y, x + dx, y)
        c.line(x, y, x, y + dy)


def draw_fssp_emblem(c, width, height):
    if not EMBLEM_PATH.exists():
        return
    try:
        emblem_size = 80
        x = width / 2 - emblem_size / 2
        y = height - 120 - emblem_size / 2
        c.drawImage(
            str(EMBLEM_PATH), x, y,
            width=emblem_size, height=emblem_size,
            preserveAspectRatio=True, mask="auto"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка герба: {e}")


async def generate_certificate(
    test_state: CurrentTestState,
    user_id: str
) -> io.BytesIO:
    """Генерирует PDF сертификат и возвращает BytesIO."""
    font = register_fonts()
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Фон
    c.setFillColor(colors.HexColor("#f7fbf7"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    draw_decorative_border(c, width, height)
    draw_fssp_emblem(c, width, height)

    # Заголовок
    c.setFont(font, 32)
    c.setFillColor(colors.HexColor("#006400"))
    c.drawCentredString(width / 2, height - 200, "СЕРТИФИКАТ")

    c.setFont(font, 14)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawCentredString(width / 2, height - 225, "о прохождении профессионального тестирования")

    c.setStrokeColor(colors.HexColor("#d4af37"))
    c.setLineWidth(2)
    c.line(150, height - 240, width - 150, height - 240)

    # Данные сотрудника
    y_pos = height - 280
    left_margin = 100
    for label, value in [
        ("ФИО:", test_state.full_name),
        ("Должность:", test_state.position),
        ("Подразделение:", test_state.department),
    ]:
        c.setFont(font, 11)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(left_margin, y_pos, label)
        c.setFillColor(colors.black)
        c.drawString(left_margin + 120, y_pos, value)
        y_pos -= 25

    y_pos -= 10
    c.setStrokeColor(colors.HexColor("#dddddd"))
    c.setLineWidth(1)
    c.line(100, y_pos, width - 100, y_pos)
    y_pos -= 30

    # Результаты
    c.setFont(font, 13)
    c.setFillColor(colors.HexColor("#006400"))
    c.drawCentredString(width / 2, y_pos, "РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    y_pos -= 30

    for label, value in [
        ("Специализация:", test_state.specialization.upper()),
        ("Уровень сложности:", test_state.difficulty.value.capitalize()),
        ("", ""),
        ("Оценка:", test_state.grade.upper()),
        ("Правильных ответов:", f"{test_state.correct_count} из {test_state.total_questions}"),
        ("Результат:", f"{test_state.percentage:.1f}%"),
        ("Затрачено времени:", test_state.elapsed_time),
    ]:
        if label:
            c.setFont(font, 10)
            c.setFillColor(colors.HexColor("#555555"))
            c.drawString(left_margin, y_pos, label)
            if label == "Оценка:":
                grade_colors = {
                    "ОТЛИЧНО": "#2d8c2d", "ХОРОШО": "#5a9fd4",
                    "УДОВЛЕТВОРИТЕЛЬНО": "#f39c12"
                }
                color = grade_colors.get(value, "#c0392b")
                c.setFillColor(colors.HexColor(color))
                c.setFont(font, 12)
            else:
                c.setFillColor(colors.black)
            c.drawString(left_margin + 150, y_pos, value)
        y_pos -= 22

    # Подвал
    footer_y = 120
    c.setStrokeColor(colors.HexColor("#006400"))
    c.setLineWidth(1)
    sw = 200
    c.line(width / 2 - sw / 2, footer_y, width / 2 + sw / 2, footer_y)

    c.setFont(font, 8)
    c.setFillColor(colors.HexColor("#777777"))
    c.drawCentredString(width / 2, footer_y - 15, "ФССП РОССИИ")
    c.drawCentredString(width / 2, footer_y - 27, "Система тестирования профессиональной подготовки")

    date_str = datetime.now().strftime("%d.%m.%Y")
    c.drawString(80, 50, f"Дата выдачи: {date_str}")
    c.drawRightString(width - 80, 50, f"ID: {user_id}")
    c.setFont(font, 7)
    c.setFillColor(colors.HexColor("#bbbbbb"))
    c.drawCentredString(width / 2, 50, "VK Workspace Bot")

    c.save()
    buffer.seek(0)
    logger.info(f"✅ Сертификат сгенерирован для {user_id}")
    return buffer
