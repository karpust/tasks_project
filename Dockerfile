# облегченный питон, без лишнего:
FROM python:3.10-slim

# запрещаю питону создавать файлы байт-кода(.pyc) для ускорения:
ENV PYTHONDONTWRITEBYTECODE 1

# отключаю буферизацию вывода питона (логи будут сразу видны):
ENV PYTHONUNBUFFERED 1

# устанавливаю рабочую директорию внутри контейнера:
WORKDIR /code

# системные пакеты, для psycopg2 (postgre)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# копирую файл зависимостей в рабочую директорию контейнера
COPY requirements.txt .

# на всякий обновляю пип и устанавливаю зависимости,
# отключая кэширование пакетов pip - экономлю место:
RUN pip3 install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY wait-for-postgres.sh .
RUN chmod +x wait-for-postgres.sh  # делаю выполнимым (чтобы запускать)

# копирую все из текущей дир в WORKDIR контейнера:
COPY . .

# запускаею Gunicorn сервер,
# указывая точку входа приложения и порт, говорю сначала дождаться постгре:
CMD ["./wait-for-postgres.sh", "gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000"]
# команда по умолчанию, которая запускается при старте контейнера
# ждать пока запустится postgres
# запуск Gunicorn
# брать объект application из app.wsgi
# `--bind 0.0.0.0:8000` - запуск серверf, кот слушает все интерфейсы на порту 8000
