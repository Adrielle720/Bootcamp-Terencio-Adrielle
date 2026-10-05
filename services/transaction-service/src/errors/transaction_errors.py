from errors.base_error import QIException


class AccountNotFound(QIException):
    code = "QIT002020"

    def __init__(self, account_key) -> None:
        title = "Account not found"
        http_status = 404
        description = f"There is no account {account_key} for this customer."
        translation = "Conta não encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotAvailable(QIException):
    code = "QIT002026"

    def __init__(self, account_key) -> None:
        title = "Account is not in the right status"
        http_status = 409
        description = f"The account {account_key} cannot receive or send money in its current status."
        translation = "A conta não está em um estado que permite esta operação."
        super().__init__(title, self.code, http_status, description, translation)


class DestinationNotFound(QIException):
    code = "QIT002041"

    def __init__(self) -> None:
        title = "Destination not found"
        http_status = 404
        description = "The destination account or its holder could not be found."
        translation = "Não foi possível localizar o destino da transferência."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientBalance(QIException):
    code = "QIT002046"

    def __init__(self, account_key) -> None:
        title = "Insufficient balance"
        http_status = 422
        description = f"The account {account_key} does not have enough balance to cover the amount and the fee."
        translation = "Saldo insuficiente para cobrir o valor e a tarifa."
        super().__init__(title, self.code, http_status, description, translation)


class IdempotencyConflict(QIException):
    code = "QIT002047"

    def __init__(self, idempotency_key) -> None:
        title = "Idempotency key reused with a different body"
        http_status = 422
        description = f"The Idempotency-Key {idempotency_key} was already used with a different request."
        translation = "Esta chave de idempotência já foi usada com outro pedido."
        super().__init__(title, self.code, http_status, description, translation)


class TransferLimitExceeded(QIException):
    code = "QIT002044"

    def __init__(self, account_key) -> None:
        title = "Transfer limit exceeded"
        http_status = 422
        description = f"The amount exceeds the transfer limit of the account {account_key}."
        translation = "O valor ultrapassa o limite por transferência desta conta."
        super().__init__(title, self.code, http_status, description, translation)
