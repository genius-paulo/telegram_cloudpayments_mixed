from aiogram import Bot, Dispatcher, executor, types
from loguru import logger
from config import settings
from cloud_payments import cloud_payments, models
from cloud_payments.models import Order
from db_infra import db

bot = Bot(token=settings.tg_token)
dp = Dispatcher(bot)
client = cloud_payments.CloudPayments(settings.cp_p_id, settings.cp_api_pass)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Hi!\nThe bot is working.")
    await message.reply(f"Available tables in db: {db.db.get_tables()}")


@dp.message_handler(commands=["get_payment"])
async def get_payment_link(message: types.Message):
    try:
        # Сюда нужно передавать сумму из сообщения
        order = await client.create_order_link(10.0, 'USD', message.from_id)
        await message.answer(f'Your order link: {order.url}')

        # Запускаем polling-проверку статуса платежа
        await check_order_status(order)
    except Exception as e:
        await message.answer(f'Somethings went wrong: {e}')


async def check_order_status(order: Order) -> Order:
    order = await client.check_order_polling(order)

    if order.status_code == models.StatusCode.ok.value:
        order = await payment_received(order)

    elif order.status_code in (models.StatusCode.error.value,
                               models.StatusCode.cancel.value,
                               models.StatusCode.max_attempts):
        order = await cancel_payment(order)

    return order


# Действия при удачной оплате
async def payment_received(order: Order):
    logger.info(f"The payment {order.number} received")
    # Сообщение для понимания, что платеж прошел успешно
    # TODO: Добавить в модель account_id, пока здесь мой айдишник
    await bot.send_message('542570177',
                           f'The payment {order.number} was successful.'
                           f'\nThe amount: {order.amount}.')


# Действия при неудачной оплате
async def cancel_payment(order: Order):
    order = await client.cancel_payment(order)
    logger.info(f"The payment {order.number} canceled")
    # Сообщение для понимания, что платеж прошел с ошибкой
    # TODO: Добавить в модель account_id, пока здесь мой айдишник
    await bot.send_message('542570177',
                           f'The payment {order.number} was made with an error.'
                           f'\nThe amount of {order.amount} has not been credited.'
                           f'\nStatus code: {order.status_code}')


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=settings.skip_updates)