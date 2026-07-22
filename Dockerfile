# Персональный научный сайт — Усманов Рустамжон (Flask)
FROM python:3.12-slim

# DejaVu-шрифты нужны reportlab для генерации CV (pdf_cv.py -> /usr/share/fonts/truetype/dejavu)
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала зависимости — кэшируется, пока requirements.txt не изменится
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем исходники
COPY . .

# Слушаем порт 80 — обратный прокси dotachamp-nginx-1 проксирует на sapsite:80.
# Порт <1024, поэтому внутри контейнера работаем от root (контейнер в приватной docker-сети).
EXPOSE 80

# Прод-сервер: приложение = объект `app` в app.py
# timeout 60 — с запасом на генерацию CV в PDF
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "3", "--timeout", "60", "app:app"]
