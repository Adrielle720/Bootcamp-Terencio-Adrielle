from errors.base_error import QIException


class CustomerNotFound(QIException):
    code = "QIT002010"

    def __init__(self, customer_key) -> None:
        title = "Customer not found"
        http_status = 404
        description = f"There is no customer with the key {customer_key}."
        translation = "Cliente não encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotFound(QIException):
    code = "QIT002020"

    def __init__(self, account_key) -> None:
        title = "Account not found"
        http_status = 404
        description = f"There is no account with the key {account_key} for this customer."
        translation = "Conta não encontrada."
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

    def __init__(self, contact) -> None:
        title = "Invalid invitation"
        http_status = 422
        description = f"The contact {contact} cannot be invited: it is the master or was already invited."
        translation = "Este contato não pode ser convidado para esta conta."
        super().__init__(title, self.code, http_status, description, translation)


class NoSeatsLeft(QIException):
    code = "QIT002025"

    def __init__(self) -> None:
        title = "No seats left"
        http_status = 409
        description = "The account already has six holders."
        translation = "A conta já tem seis participantes."
        super().__init__(title, self.code, http_status, description, translation)


class AccountInWrongStatus(QIException):
    code = "QIT002026"

    def __init__(self, account_key) -> None:
        title = "Account is not in the right status"
        http_status = 409
        description = f"The account {account_key} is not in the status required for this operation."
        translation = "A conta não está no estado necessário para esta operação."
        super().__init__(title, self.code, http_status, description, translation)


class NotMaster(QIException):
    code = "QIT002028"

    def __init__(self, customer_key) -> None:
        title = "Only the master can do this"
        http_status = 422
        description = f"The customer {customer_key} is not the master of this account."
        translation = "Só o master da conta pode fazer isso."
        super().__init__(title, self.code, http_status, description, translation)


class HolderIsNotMinor(QIException):
    code = "QIT002029"

    def __init__(self, holder_key) -> None:
        title = "Holder is not a minor"
        http_status = 422
        description = f"The holder {holder_key} is not a minor, so it has no monthly limit."
        translation = "O limite mensal vale só para titulares menores de idade."
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


class ContactAlreadyInvited(QIException):
    code = "QIT002032"

    def __init__(self, contact) -> None:
        title = "Contact already has a pending invitation"
        http_status = 409
        description = f"The contact {contact} already has a pending invitation."
        translation = "Este contato já tem um convite pendente."
        super().__init__(title, self.code, http_status, description, translation)


class CustomerNotApproved(QIException):
    code = "QIT002033"

    def __init__(self, customer_key) -> None:
        title = "Customer is not approved"
        http_status = 422
        description = f"The customer {customer_key} has not had the documents approved yet."
        translation = "O cadastro ainda não foi aprovado: envie e aguarde a análise dos documentos."
        super().__init__(title, self.code, http_status, description, translation)


class HolderIsNotMinorForGuardianship(QIException):
    code = "QIT002034"

    def __init__(self, holder_key) -> None:
        title = "Holder is not a minor"
        http_status = 422
        description = f"The holder {holder_key} is not a minor waiting for a guardian."
        translation = "Este titular não é um menor de idade da conta."
        super().__init__(title, self.code, http_status, description, translation)


class GuardianNotActiveAdult(QIException):
    code = "QIT002035"

    def __init__(self, customer_key) -> None:
        title = "Guardian must be an active adult holder"
        http_status = 422
        description = f"The customer {customer_key} is not an active adult holder of this account."
        translation = "O responsável precisa ser um titular adulto ativo da conta."
        super().__init__(title, self.code, http_status, description, translation)


class MissingGuardianshipDocument(QIException):
    code = "QIT002036"

    def __init__(self, missing) -> None:
        title = "Missing guardianship document"
        http_status = 422
        description = f"The kinship degree requires the document: {missing}."
        translation = "Falta um documento exigido para este grau de parentesco."
        super().__init__(title, self.code, http_status, description, translation)


class MinorAlreadyHasGuardian(QIException):
    code = "QIT002037"

    def __init__(self, holder_key) -> None:
        title = "Minor already has a guardian"
        http_status = 409
        description = f"The minor {holder_key} already has an approved guardianship."
        translation = "Este menor já tem um responsável aprovado."
        super().__init__(title, self.code, http_status, description, translation)


class GuardianshipNotFound(QIException):
    code = "QIT002038"

    def __init__(self, guardianship_key) -> None:
        title = "Guardianship not found"
        http_status = 404
        description = f"There is no guardianship {guardianship_key} for this customer."
        translation = "Guarda não encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class DestinationNotFound(QIException):
    code = "QIT002041"

    def __init__(self) -> None:
        title = "Destination not found"
        http_status = 404
        description = "The destination account or its holder could not be found."
        translation = "Não foi possível localizar o destino da transferência."
        super().__init__(title, self.code, http_status, description, translation)


class IdempotencyConflict(QIException):
    code = "QIT002047"

    def __init__(self, idempotency_key) -> None:
        title = "Idempotency key reused with a different body"
        http_status = 422
        description = f"The Idempotency-Key {idempotency_key} was already used with a different request."
        translation = "Esta chave de idempotência já foi usada com outro pedido."
        super().__init__(title, self.code, http_status, description, translation)


class ServiceUnavailable(QIException):
    code = "QIT002090"

    def __init__(self, service_name) -> None:
        title = "Dependent service unavailable"
        http_status = 503
        description = f"The {service_name} did not respond in time. Nothing was recorded; retry with the same key."
        translation = "Um serviço interno não respondeu. Nada foi gravado; tente de novo."
        super().__init__(title, self.code, http_status, description, translation)
