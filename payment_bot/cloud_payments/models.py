import enum


class Model(object):
    @classmethod
    def from_dict(cls, model_dict):
        raise NotImplementedError

    def __repr__(self):
        state = ['%s=%s' % (k, repr(v)) for (k, v) in vars(self).items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(state))


# Модель заказа с заполнением из JSON
class Order(Model):
    def __init__(self, id, number, amount, currency, email,
                 description, require_confirmation, url, status_code, created):
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

    @classmethod
    def from_dict(cls, order_dict):
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


# Модель заказа с заполнением из JSON
class Transaction(Model):
    def __init__(self, transaction_id, invoice_id, amount, currency,
                 description, status_code, status):
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
        return cls(order_dict['TransactionId'],
                   order_dict['InvoiceId'],
                   order_dict['Amount'],
                   order_dict['Currency'],
                   order_dict['Description'],
                   order_dict['StatusCode'],
                   order_dict['Status'])


# Модель данных для статус-кодов платежа
class StatusCode(enum.Enum):
    # Наши кастомные коды для полинга
    cancel: int = -1  # Платеж отменен с нашей стороны
    max_attempts: int = -2  # Бот потратил попытки для опроса платежа: delay * max_attempts в config.settings

    # Коды CloudPayments
    wait: int = 1  # В платеж перешли и ввели карту, но не подтвердили
    ok: int = 2  # Платеж прошел успешно
    error: int = 5  # Платеж явно отклонен CloudPayments
