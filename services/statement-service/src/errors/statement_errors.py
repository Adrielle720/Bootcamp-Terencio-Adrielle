from errors.base_error import QIException


class AccountNotFound(QIException):
    code = "QIT002020"

    def __init__(self, account_key) -> None:
        title = "Account not found"
        http_status = 404
        description = f"There is no account {account_key} for this customer."
        translation = "Conta não encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class TransactionNotFound(QIException):
    code = "QIT002050"

    def __init__(self, transaction_key) -> None:
        title = "Transaction not found"
        http_status = 404
        description = f"There is no transaction {transaction_key} in this account."
        translation = "Operação não encontrada nesta conta."
        super().__init__(title, self.code, http_status, description, translation)
