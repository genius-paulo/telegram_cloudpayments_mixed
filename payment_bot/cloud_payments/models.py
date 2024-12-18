import enum


class Model(object):
    """Класс для объектов CLoudPayments"""

    @classmethod
    def from_dict(cls, model_dict):
        raise NotImplementedError

    def __repr__(self):
        state = ['%s=%s' % (k, repr(v)) for (k, v) in vars(self).items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(state))


class Order(Model):
    """Класс заказа. Используется для:
    формирования заказа на стороне клиента, создания заказа в CloudPayments,
    синхронизации данных транзакции в CloudPayments с заказом на нашей стороне и в БД.
    Заполняется из словаря с помощью метода from_dict()"""

    def __init__(self, id, number, amount, currency, email,
                 description, require_confirmation, url, status_code, created, receipt_url=None):
        """Метод инициализации"""
        super(Order, self).__init__()
        self.id = id
        self.number = number
        self.amount = amount
        self.currency = currency
        self.email = email
        self.description = description
        self.require_confirmation = require_confirmation
        self.url = url
        self.status_code = status_code
        self.created = created
        self.receipt_url = receipt_url

    @classmethod
    def from_dict(cls, order_dict):
        """Преобразует элементы словаря, который передает CloudPayments в атрибуты инстанса"""
        return cls(order_dict['Id'],
                   order_dict['Number'],
                   order_dict['Amount'],
                   order_dict['Currency'],
                   order_dict['Email'],
                   order_dict['Description'],
                   order_dict['RequireConfirmation'],
                   order_dict['Url'],
                   order_dict['StatusCode'],
                   order_dict['CreatedDateIso'])


class Transaction(Model):
    """Класс транзацкции. Используется для получения обновлений о нашем заказе в CloudPayments.
    Когда пользователь ввел карту, заказ на стороне CloudPayments становится транзакцией.
    Заполняется из словаря с помощью метода from_dict()"""

    def __init__(self, transaction_id, invoice_id, amount, currency,
                 description, status_code, status):
        """Метод инициализации"""
        super(Transaction, self).__init__()
        self.transaction_id = transaction_id
        self.invoice_id = invoice_id
        self.amount = amount
        self.currency = currency
        self.description = description
        self.status_code = status_code
        self.status = status

    @classmethod
    def from_dict(cls, order_dict):
        """Преобразует элементы словаря, который передает CloudPayments в атрибуты инстанса"""

        return cls(order_dict['TransactionId'],
                   order_dict['InvoiceId'],
                   order_dict['Amount'],
                   order_dict['Currency'],
                   order_dict['Description'],
                   order_dict['StatusCode'],
                   order_dict['Status'])


class StatusCode(enum.Enum):
    """Класс статус-кодов, чтобы передавать их в более явном виде"""

    # Наши кастомные коды для полинга
    cancel: int = -1  # Платеж отменен с нашей стороны
    max_attempts: int = -2  # Бот потратил попытки для опроса платежа: delay * max_attempts в config.settings

    # Коды CloudPayments
    wait: int = 1  # В платеж перешли и ввели карту, но не подтвердили
    ok: int = 2  # Платеж прошел успешно
    error: int = 5  # Платеж явно отклонен CloudPayments


class Receipt(Model):
    """Объект чека. Содержит важные поля для создания чека на стороне CloudPayments.
    Преобразуется в словарь с помощью метода to_dict()"""

    def __init__(self, items: list, taxation_system: str, email: str = '', phone: str = '', amounts: dict = None):
        """Метод инициализации"""
        self.items = items
        self.taxation_system = taxation_system
        self.email = email
        self.phone = phone
        self.amounts = amounts

    def to_dict(self):
        """Преобразует атрибуты инстанса в словарь для отправки в CloudPayments"""
        items = [item.to_dict() for item in self.items]
        result = {
            'items': items,
            'taxationSystem': self.taxation_system,
            'email': self.email,
            'phone': self.phone,
        }
        return result


# Модель для позиций в чеке
class ReceiptItem(Model):
    """Объект одной позиции в чеке. Для CloudPayments каждую позицию нужно подробно расписывать."""

    def __init__(self, label, price, quantity, amount, vat, ean13=None,
                 method=0, item_object=0, measurement_unit=None):
        """Метод инициализации"""
        self.label = label
        self.price = price
        self.quantity = quantity
        self.amount = amount
        self.vat = vat  # ставка НДС
        self.ean13 = ean13
        self.method = method  # признак способа расчета
        self.item_object = item_object  # признак предмета товара (10 — Payment, платеж)
        self.measurement_unit = measurement_unit  # единица измерения

    def to_dict(self):
        """Преобразует атрибуты инстанса в словарь для отправки в CloudPayments"""
        return {
            'label': self.label,
            'price': self.price,
            'quantity': self.quantity,
            'amount': self.amount,
            'vat': self.vat,
            'ean13': self.ean13,
            'method': self.method,
            'object': self.item_object,
            'measurementUnit': self.measurement_unit
        }