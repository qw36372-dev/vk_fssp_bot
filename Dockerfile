FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей (шрифты для reportlab)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директорий для данных
RUN mkdir -p data logs

# Запуск бота
CMD ["python3", "main.py"]
