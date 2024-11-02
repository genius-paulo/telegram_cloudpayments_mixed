from fastapi import FastAPI, Request
from urllib.parse import parse_qs
from time import sleep
from asyncio import sleep as asleep
from aiogram import types, Dispatcher, Bot
from loguru import logger
from payment_bot.config import settings
from payment_bot.cloud_payments import cloud_payments, models
from payment_bot.cloud_payments.models import Order
from payment_bot.db_infra import db

# Запускаем бота
bot = Bot(token=settings.tg_token)
dp = Dispatcher(bot)

# Создаем клиента для CloudPayments
client = cloud_payments.CloudPayments(settings.cp_p_id, settings.cp_api_pass)

# Создаем таблицу
db.create_tables(db.db, db.Orders)

# Создаем сервер FastAPI
app = FastAPI()
logger.debug('Start webhook mode')


# ---- FastAPI handlers ---- #
# Устанавливает WEBHOOK URL при запуске
@app.on_event("startup")
async def on_startup():
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != f"{settings.ngrok_url}{settings.webhook_path}":
        await bot.set_webhook(
            url=f"{settings.ngrok_url}{settings.webhook_path}"
        )
    # Реализация skip_updates
    if settings.skip_updates:
        await bot.delete_webhook(drop_pending_updates=True)
        sleep(1)
        await asleep(0)
        await bot.set_webhook(
            url=f"{settings.ngrok_url}{settings.webhook_path}"
        )


# Доставляет изменения боту при получении POST запроса от Telegram API
@app.post(settings.webhook_path)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    Dispatcher.set_current(dp)
    Bot.set_current(bot)
    await dp.process_update(telegram_update)


# Закрывает сессию бота и удаляет вебхук
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    session = await bot.get_session()
    await session.close()


# Хук для успешной оплаты CloudPayments
@app.post("/pay")
async def receive_webhook(request: Request):
    logger.debug(f"Type of request.body(): {type(await request.body())}")
    # Обрабатываем запрос, пришедший по хуку, изменяем нужный Order
    new_order = await get_transaction_webhook(await request.body(),
                                              status_code=models.StatusCode.ok.value)
    logger.debug(new_order)


# Хук для ошибки оплаты CloudPayments
@app.post("/fail")
async def receive_webhook(request: Request):
    logger.debug(f"Type of request.body(): {type(await request.body())}")
    # Обрабатываем запрос, пришедший по хуку, изменяем нужный Order
    new_order = await get_transaction_webhook(await request.body(),
                                              status_code=models.StatusCode.error.value)
    logger.debug(new_order)
# ------------------------- #


# ---- Telegram Bot handlers ---- #
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply("Hi!\nThe bot is working.")
    await message.reply(f"Available tables in db: {db.db.get_tables()}")


@dp.message_handler(commands=["get_payment"])
async def get_payment_link(message: types.Message):
    try:
        # Сюда нужно передавать сумму из сообщения
        order = await client.create_order_link(10.0, 'USD', message.from_id)
        # Создаем платеж в базе
        order = await db.add_order(order)

        logger.debug(f"Order created: {order}")
        await message.answer(f'Your order link: {order.url}')
    except Exception as e:
        await message.answer(f'Somethings went wrong: {e}')


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)
# ------------------------- #


# ---- Bot payment processing ---- #
# Проверяем статус платежа разово вручную
async def check_order_status(order: Order) -> Order:
    order = await client.check_order(order)

    if order.status_code == models.StatusCode.ok.value:
        await payment_received(order)

    elif order.status_code in (models.StatusCode.error.value,
                               models.StatusCode.cancel.value,
                               models.StatusCode.max_attempts):
        order = await cancel_payment(order)

    elif order.status_code == models.StatusCode.wait.value:
        await payment_is_waiting(order)

    return order


# Действия при ручной проверке статуса платежа
async def payment_is_waiting(order: Order):
    logger.info(f"The payment {order.number} is waiting")
    order = await db.update_order(order)
    # Сообщение для понимания, что платеж прошел успешно
    await bot.send_message(order.description,
                           f'The payment {order.number} is waiting.')


# Действия при удачной оплате
async def payment_received(order: Order):
    order = await db.update_order(order)
    logger.info(f"The payment {order.number} received. Status: {order.status_code}")
    # Сообщение для понимания, что платеж прошел успешно
    await bot.send_message(order.description,
                           f'The payment {order.number} was successful.'
                           f'\nThe amount: {order.amount}.')


async def get_transaction_webhook(request_body: bytes, status_code: int):
    # Преобразуем байты в строку, разбираем строку запроса и добавляем статус-код
    decoded_body = request_body.decode('utf-8')
    params_dict = parse_qs(decoded_body)
    params_dict['StatusCode'] = [str(status_code)]

    # Обновляем объект платежа
    transaction = models.Transaction.from_dict(params_dict)
    logger.debug(f"Transaction has been created from dict: {transaction}")

    order = await db.get_order_by_number(transaction.invoice_id)
    logger.debug(f"Order has been created from dict: {order}")

    new_order = client.update_order(transaction.status_code, order)
    new_order = await db.update_order(new_order)
    logger.debug(f"Order was updated: {new_order}")

    return new_order


# Действия при неудачной оплате
async def cancel_payment(order: Order):
    order = await client.cancel_payment(order)
    await db.update_order(order)
    logger.info(f"The payment {order.number} canceled")
    # Сообщение для понимания, что платеж прошел с ошибкой
    await bot.send_message(order.description,
                           f'The payment {order.number} was made with an error.'
                           f'\nThe amount of {order.amount} has not been credited.'
                           f'\nStatus code: {order.status_code}')
# ------------------------- #
