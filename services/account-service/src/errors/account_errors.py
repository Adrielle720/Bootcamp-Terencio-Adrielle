from errors.base_error import QIException


class CustomerNotFound(QIException):
    code = "QIT002010"

    def __init__(self, customer_key) -> None:
        title = "Customer not found"
        http_status = 404
        description = f"There is no customer with the key {customer_key}."
        translation = "Cliente não encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class CustomerNotFoundByPhone(QIException):
    code = "QIT002023"

    def __init__(self, phone) -> None:
        title = "Customer not found by phone"
        http_status = 404
        description = f"There is no customer with the phone {phone}."
        translation = "Não existe cliente cadastrado com este telefone."
        super().__init__(title, self.code, http_status, description, translation)


class MasterIsUnderage(QIException):
    code = "QIT002021"

    def __init__(self, age, minimum_age) -> None:
        title = "Master is underage"
        http_status = 422
        description = f"The master is {age} years old, and the minimum is {minimum_age}."
        translation = f"O master da conta precisa ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class CustomerAlreadyInAccount(QIException):
    code = "QIT002022"

    def __init__(self, customer_key) -> None:
        title = "Customer already in an account"
        http_status = 409
        description = f"The customer {customer_key} already has an account or a pending invitation."
        translation = "Esta pessoa já participa de outra conta ou tem um convite pendente."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidInvitation(QIException):
    code = "QIT002024"

    def __init__(self, phone) -> None:
        title = "Invalid invitation"
        http_status = 422
        description = f"The phone {phone} cannot be invited: it is the master or was already invited."
        translation = "Este telefone não pode ser convidado para esta conta."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotFound(QIException):
    code = "QIT002020"

    def __init__(self, account_key) -> None:
        title = "Account not found"
        http_status = 404
        description = f"There is no account with the key {account_key} for this customer."
        translation = "Conta não encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class NoSeatsLeft(QIException):
    code = "QIT002025"

    def __init__(self) -> None:
        title = "No seats left"
        http_status = 409
        description = "The account already has six holders."
        translation = "A conta já tem seis participantes."
        super().__init__(title, self.code, http_status, description, translation)


class HolderNotFound(QIException):
    code = "QIT002030"

    def __init__(self, holder_key) -> None:
        title = "Invitation not found"
        http_status = 404
        description = f"There is no invitation {holder_key} for this customer."
        translation = "Convite não encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class HolderNotPending(QIException):
    code = "QIT002031"

    def __init__(self, holder_key) -> None:
        title = "Invitation is not pending"
        http_status = 409
        description = f"The invitation {holder_key} is no longer pending."
        translation = "Este convite não está mais pendente."
        super().__init__(title, self.code, http_status, description, translation)
