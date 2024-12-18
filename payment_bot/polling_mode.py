from aiogram import Bot, Dispatcher, executor, types
from loguru import logger
from config import settings
from cloud_payments import cloud_payments, models
from cloud_payments.models import Order
from db_infra import db

# Запускаем бота
bot = Bot(token=settings.tg_token)
dp = Dispatcher(bot)

# Создаем клиента для CloudPayments
client = cloud_payments.CloudPayments(settings.cp_p_id, settings.cp_api_pass)

# Создаем бд
db.create_tables(db.db, db.Orders)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Проверяем, что все ок и что бот работает"""
    await message.reply("Hi!\nThe bot is working.")
    await message.reply(f"Available tables in db: {db.db.get_tables()}")


@dp.message_handler(commands=["get_payment"])
async def get_payment_link(message: types.Message) -> None:
    """Создаем платеж в CloudPayments, добавляем в БД,
    отправляем юзеру ссылку, запускаем polling-проверку"""
    try:
        # Сюда нужно передавать сумму из сообщения
        order = await client.create_order_link(10.0, 'USD', message.from_id)
        await message.answer(f'Your order link: {order.url}')

        # Создаем платеж в базе
        await db.add_order(order)

        # Запускаем polling-проверку статуса платежа
        await check_order_status(order)
    except Exception as e:
        await message.answer(f'Somethings went wrong: {e}')


async def check_order_status(order: Order):
    """Запускаем проверку статуса заказа в CloudPayments и реагируем на изменения статусов.
    Если лимит проверок закончился, получили ошибку или платеж отменился, руками отменяем платеж,
    чтобы не наткнуться на ошибку."""
    order = await client.check_order_polling(order)
    if order.status_code == models.StatusCode.ok.value:
        await payment_received(order)
    elif order.status_code in (models.StatusCode.error.value,
                               models.StatusCode.cancel.value,
                               models.StatusCode.max_attempts):
        await cancel_payment(order)


async def payment_received(order: Order) -> None:
    """Действия при удачной оплате: обновляем объект заказа в БД, отсылаем подрообности юзеру"""
    # Получаем ссылку на чек и отправляем юзеру
    updated_order = await get_receipt(order)
    order = await db.update_order(order)
    logger.info(f"The payment {order.number} received. Status: {order.status_code}")
    # Сообщение для понимания, что платеж прошел успешно
    await bot.send_message(order.description,
                           f'The payment {order.number} was successful.'
                           f'\nThe amount: {order.amount}.')
    await bot.send_message(order.description,
                           f'Your receipt link: {updated_order.receipt_url}')


async def cancel_payment(order: Order) -> None:
    """Действия при неудачной оплате: отменяем платеж в CloudPayments,
    обновляем статус платежа в БД, отправляем инфу юзеру"""
    order = await client.cancel_payment(order)
    await db.update_order(order)
    logger.info(f"The payment {order.number} canceled")
    # Сообщение для понимания, что платеж прошел с ошибкой
    await bot.send_message(order.description,
                           f'The payment {order.number} was made with an error.'
                           f'\nThe amount of {order.amount} has not been credited.'
                           f'\nStatus code: {order.status_code}')


async def get_receipt(order: Order) -> Order:
    """Получаем чек, добавляем его к объекту платежа"""
    receipt_item = models.ReceiptItem(label=order.description,
                                      price=str(order.amount),
                                      # TODO: Пока у нас один товар на одну оплату
                                      #  Возможно, со временем понадобится расширять функциональность
                                      quantity='1',
                                      amount=str(order.amount),
                                      vat=settings.vat,
                                      item_object='10')
    customer_receipt_obj = models.Receipt(items=[receipt_item],
                                          taxation_system=settings.tax_system,
                                          amounts={'Electronic': str(order.amount)})

    order.receipt_url = await client.create_receipt_url(customer_receipt_obj)
    logger.debug(f'Get receipt link: {order.receipt_url}')
    return order


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer('This bot demonstrates the possibilities of interacting with the Cloud Payments API.'
                         ' To receive a test payment, click /get_payment')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=settings.skip_updates)
