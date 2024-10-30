# Используем официальный образ Python в качестве базового образа
FROM python

ADD payment_bot /usr/src/app/payment_bot

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /usr/src/app/payment_bot

COPY poetry.lock pyproject.toml ./

RUN pip --no-cache-dir install poetry

RUN poetry install --no-interaction --no-ansi