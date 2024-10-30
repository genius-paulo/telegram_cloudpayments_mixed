from httpx import AsyncClient, BasicAuth
from payment_bot.config import settings
from loguru import logger
import asyncio
from payment_bot.cloud_payments.models import Order, Transaction, StatusCode
import decimal
import json


class CloudPayments:
    URL = 'https://api.cloudpayments.ru/'

    def __init__(self, cp_public_id, api_password):
        self.cp_public_id = cp_public_id
        self.api_password = api_password

    # Внутренний универсальный метод для создания асинхронного запроса
    async def _send_request(self, endpoint, params=None) -> json:
        auth = BasicAuth(self.cp_public_id, self.api_password)
        async with AsyncClient() as async_client:
            async_response = await async_client.post(url=self.URL + endpoint,
                                                     auth=auth,
                                                     json=params)
            return async_response.json(parse_float=decimal.Decimal)

    # Метод для создания платежной ссылки
    async def create_order_link(self, amount, currency, description) -> Order:
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

    # Метод для разовой проверки платежа
    async def check_order(self, order: Order) -> Order:
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

    # Метод для polling-проверки платежа
    async def check_order_polling(self, order: Order) -> Order:
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

    # Метод для ручного удаления платежа
    async def cancel_payment(self, order: Order) -> Order:
        endpoint = 'orders/cancel'
        params = {"Id": order.id}

        response = await self._send_request(endpoint, params)
        logger.info(f"Deleting order {order.number}. Response: {response}")
        order.status_code = StatusCode.cancel.value

        return order

    def update_order(self, status_code: int, order: Order) -> Order:
        order.status_code = status_code
        logger.info(f"Update order {order.number}. Status: {order.status_code}")
        return order


# TODO: Почему оно запускается, даже когда имортируется?
if __name__ == '__main__':
    """
    client = CloudPayments(settings.cp_p_id, settings.cp_api_pass)
    order = asyncio.run(client.create_order_link(10,
                                                 'USD',
                                                 'Top up your account'))
    logger.info(order)

    checked_order = asyncio.run(client.check_order(order))
    logger.debug(f"Check order for webhook: {checked_order}")
    checked_order = asyncio.run(client.check_order_polling(order))
    logger.debug(f"Check order for polling: {checked_order}")
    logger.info(checked_order)
    """
    pass
