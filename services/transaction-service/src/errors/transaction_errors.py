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
