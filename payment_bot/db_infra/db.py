import peewee
import peewee_async
from peewee import *
from loguru import logger
import asyncio
from payment_bot.cloud_payments.models import Order
import datetime

from payment_bot.config import settings

# Подключение к базе данных PostgreSQL
db = peewee_async.PostgresqlDatabase(database=settings.db_name,
                                     user=settings.db_user, password=settings.db_password,
                                     host=settings.db_host)


class BaseModel(Model):
    id = TextField(column_name='id', null=False)
    number = TextField(column_name='number', null=False)
    amount = DecimalField(column_name='amount', null=False)
    currency = TextField(column_name='currency', null=False)
    email = TextField(column_name='email', null=True)
    description = TextField(column_name='description', null=True)
    require_confirmation = TextField(column_name='require_confirmation', null=True)
    url = TextField(column_name='url', null=False)
    status_code = IntegerField(column_name='status_code', null=True)
    created = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db


class Orders(BaseModel):
    class Meta:
        table_name = 'Orders'


def _get_conn() -> peewee_async.Manager:
    connection_manager = peewee_async.Manager(db)
    return connection_manager


def create_tables(database: peewee_async.PostgresqlDatabase, table: type[Orders]) -> None:
    database.create_tables([table])
    logger.info("Tables created")


# Функция для получения всех платежей из бд
async def get_orders():
    elements = await _get_conn().execute(Orders.select())
    list_elements = []
    for element in elements:
        list_elements.append(element)
    logger.debug(f"Get all of objects from db: {list_elements}")
    return list_elements


# Функция для получения платежа из бд по номеру
async def get_order_by_number(number: str):
    try:
        order = await _get_conn().get(Orders, number=number)
        logger.debug(f"Get order from db: {order.number}")
    except Exception as e:
        logger.debug(f"Something went wrong: {e}")
        return None
    else:
        return order


# Функция для создания нового платежа в бд
async def add_order(order: Order):
    new_order = await _get_conn().create(Orders,
                                         id=order.id, number=order.number, amount=order.amount, currency=order.currency,
                                         email=order.email, description=order.description,
                                         require_confirmation=order.require_confirmation, url=order.url,
                                         status_code=order.status_code)
    logger.debug(f'Order created')
    return new_order


# Функция для обновления объекта платежа в базе
async def update_order(order: Order):
    result = await _get_conn().execute(Orders.update(status_code=order.status_code).where(Orders.number == order.number))
    logger.debug(f"Update order. Result: {result}")
    updated_db_object = await get_order_by_number(order.number)
    logger.debug(f'Updated db object status code: {updated_db_object.status_code}')
    return updated_db_object


# Удаляем платеж из базы
async def delete_order(order: Order) -> None:
    result = await _get_conn().execute(Orders.delete().where(Orders.number == order.number))
    logger.debug(f"Delete order. Result: {result}")
    updated_db_object = await get_order_by_number(order.number)
    logger.debug(f'Db object deleted: {updated_db_object.status_code}')


# Команда запуска докера для тестов
# docker run --name pg-container -e POSTGRES_DB=payment_db -e POSTGRES_USER=payment_user -e POSTGRES_PASSWORD=payment_password -p 5432:5432 -d postgres:15