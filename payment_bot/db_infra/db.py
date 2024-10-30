from peewee import *
from loguru import logger

# Подключение к базе данных PostgreSQL
db = PostgresqlDatabase('payment_db',
                        user='payment_user', password='payment_password',
                        host='localhost')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    name = CharField()
    email = CharField(unique=True)


# Создаем таблицы, если они еще не существуют
db.connect()
logger.debug(db.get_tables())
db.create_tables([User])
