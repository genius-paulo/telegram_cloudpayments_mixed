from httpx import AsyncClient, BasicAuth
from payment_bot.config import settings
from loguru import logger
import asyncio
from payment_bot.cloud_payments.models import Order, Transaction, StatusCode, Receipt
import decimal
import json


class CloudPayments:
    """Класс клиента CloudPayments. Методы:
    create_order_link() — формирует платеж в системе и отдает ссылку для оплаты
    check_order() — разовая проверка статуса платежа
    check_order_polling() — перманентный метод для проверки платежа в формате polling
                            (раз в несколько секунд, определенное количество раз, в зависимости от настроек)
    cancel_payment() — отменяет платеж
    update_order() — обновляет статус-код в инстансе заказа
    create_receipt_url() — создает чек и отдает ссылочку на него"""

    # URL для обращения к API CloudPayments
    URL = 'https://api.cloudpayments.ru/'

    def __init__(self, cp_public_id, api_password):
        """Метод инициализации. Передаем public_ID и API_password из настроек CloudPayments"""
        self.cp_public_id = cp_public_id
        self.api_password = api_password

    async def _send_request(self, endpoint, params=None) -> json:
        """Универсальный внутренний метод для создания асинхронного запроса с нужными параметрами"""
        auth = BasicAuth(self.cp_public_id, self.api_password)
        async with AsyncClient() as async_client:
            async_response = await async_client.post(url=self.URL + endpoint,
                                                     auth=auth,
                                                     json=params)
            return async_response.json(parse_float=decimal.Decimal)

    async def create_order_link(self, amount, currency, description) -> Order:
        """Метод, который создает заказ в CloudPayments и возвращает объект заказа"""
        endpoint = 'orders/create'
        params = {
            "Amount": amount,
            "Currency": currency,
            "Description": description,
            "RequireConfirmation": 'true',
        }
        create_order_response = await self._send_request(endpoint, params)
        logger.debug(f"The response has been received: {create_order_response['Model']}")
        if create_order_response['Success']:
            return Order.from_dict(create_order_response['Model'])

    async def check_order(self, order: Order) -> Order:
        """Метод для разовой проверки платежа. Подходит для финальной сверки, в режиме хуков избыточен"""
        endpoint = 'payments/find'
        params = {'InvoiceId': order.number}

        # Делаем запрос
        checking_order_response = await self._send_request(endpoint, params)
        logger.debug(f"One order check {checking_order_response}")

        # Если есть Model, значит по платежу началась суета
        if 'Model' in checking_order_response:
            transaction = Transaction.from_dict(checking_order_response['Model'])
            return self.update_order(transaction.status_code, order)
        else:
            logger.info(f"Check order status {order.id}: {order.status_code}. Nothing changed")
            return order

    async def check_order_polling(self, order: Order) -> Order:
        """Метод для проверки платежа в формате polling:
        раз в несколько секунд, какое-то количество раз (в зависимости от настроек).
        Подходит, когда нет возможности работать с хуками и нужно проверять все руками."""
        endpoint = 'payments/find'
        params = {'InvoiceId': order.number}

        # Проверяем платеж раз в DELAY секунд MAX_ATTEMPTS раз
        for attempt in range(settings.max_attempts):
            if attempt == (settings.max_attempts - 1):
                return self.update_order(StatusCode.max_attempts.value, order)

            # Делаем запрос
            checking_order_response = await self._send_request(endpoint, params)
            logger.debug(f"Multiple verification for polling: {checking_order_response}")

            # Если в запросе есть Model, то началась суета по платежу, можно чекать
            if 'Model' in checking_order_response:
                transaction = Transaction.from_dict(checking_order_response['Model'])
                if transaction.status == 'Authorized' or transaction.status == 'Declined':
                    return self.update_order(transaction.status_code, order)
                elif transaction.status == 'AwaitingAuthentication':
                    order = self.update_order(transaction.status_code, order)

            # Делаем паузу между запросами проверки для polling
            await asyncio.sleep(settings.delay)

    async def cancel_payment(self, order: Order) -> Order:
        """Метод для ручного удаления платежа. Можно удалить платеж после окончания
        попыток проверки в polling-режиме, чтобы точно не пропустить платеж."""
        endpoint = 'orders/cancel'
        params = {"Id": order.id}

        response = await self._send_request(endpoint, params)
        logger.info(f"Deleting order {order.number}. Response: {response}")
        order.status_code = StatusCode.cancel.value

        return order

    # TODO: Один Бог знает, как родился этот метод, его нужно привести в порядок
    @staticmethod
    def update_order(status_code: int, order: Order) -> Order:
        """Метод обновления статуса платежа в объекте.
        Выглядит, как затуп: непонятно, почему он получился статический
        и нахрена передавать инстанс, если есть self"""
        order.status_code = status_code
        logger.info(f"Update order {order.number}. Status: {order.status_code}")
        return order

    async def create_receipt_url(self, customer_receipt: Receipt) -> str:
        """Метод для получения чека.
        Пока простой, только на оплату, не на возврат или что-то еще"""
        endpoint = 'kkt/receipt'

        customer_receipt = customer_receipt.to_dict()
        logger.debug(f'CloudPayments get the receipt object: {customer_receipt}')

        params = {
            'Inn': settings.inn,
            # Как раз здесь указываем вид операции — приход
            'Type': 'Income',
            'CustomerReceipt': customer_receipt,
        }
        logger.debug(f'CloudPayments created parameters for '
                     f'request of receipt: {params} ({type(params)})')

        create_receipt_response = await self._send_request(endpoint, params)
        logger.debug(f"The response has been received: {json.dumps(create_receipt_response, indent=4)}")
        if create_receipt_response['Success']:
            logger.debug(type(create_receipt_response['Model']['Id']))
            receipt_url = 'https://receipts.ru/' + str(create_receipt_response['Model']['Id'])
            logger.info(f'The receipt was received: {receipt_url}')
            return receipt_url
