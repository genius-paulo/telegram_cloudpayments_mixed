# Используем официальный образ Python в качестве базового образа
FROM python:3.10-bookworm

ADD payment_bot /usr/src/telegram_cloudpayments_mixed/payment_bot

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /usr/src/telegram_cloudpayments_mixed/

COPY poetry.lock pyproject.toml ./

ENV PYTHONPATH=/usr/src/telegram_cloudpayments_mixed/

RUN pip --no-cache-dir install poetry

RUN poetry export --without-hashes -f requirements.txt -o requirements.txt

RUN pip install --no-cache-dir -r requirements.txt