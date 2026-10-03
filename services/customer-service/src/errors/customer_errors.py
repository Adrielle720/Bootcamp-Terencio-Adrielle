from errors.base_error import QIException


class InvalidDocumentNumber(QIException):
    code = "QIT002001"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageCustomer(QIException):
    code = "QIT002002"

    def __init__(self, age, minimum_age) -> None:
        title = "Customer is underage"
        http_status = 422
        description = f"The customer is {age} years old, and the minimum is {minimum_age}."
        translation = f"O cadastro exige pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    code = "QIT002003"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already a customer with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT002004"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already a customer with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedPhone(QIException):
    code = "QIT002005"

    def __init__(self, phone) -> None:
        title = "Phone already registered"
        http_status = 409
        description = f"There is already a customer with the phone {phone}."
        translation = "Já existe um cadastro com este telefone."
        super().__init__(title, self.code, http_status, description, translation)


class DocumentNotFoundInBureau(QIException):
    code = "QIT002006"

    def __init__(self, document_number) -> None:
        title = "Document not found"
        http_status = 422
        description = f"The document number {document_number} was not found in the credit bureau."
        translation = "O CPF informado não existe."
        super().__init__(title, self.code, http_status, description, translation)


class IrregularDocumentInBureau(QIException):
    code = "QIT002007"

    def __init__(self, document_number) -> None:
        title = "Irregular document"
        http_status = 422
        description = f"The document number {document_number} is irregular in the credit bureau."
        translation = "O CPF informado está irregular."
        super().__init__(title, self.code, http_status, description, translation)


class BureauDataMismatch(QIException):
    code = "QIT002008"

    def __init__(self, document_number) -> None:
        title = "Data does not match the bureau"
        http_status = 422
        description = f"The name or birthdate does not match the credit bureau for {document_number}."
        translation = "Nome ou data de nascimento não conferem com o CPF informado."
        super().__init__(title, self.code, http_status, description, translation)


class BureauUnavailable(QIException):
    code = "QIT002009"

    def __init__(self) -> None:
        title = "Credit bureau unavailable"
        http_status = 502
        description = "The credit bureau did not respond in time."
        translation = "O serviço de consulta de CPF não respondeu. Tente novamente."
        super().__init__(title, self.code, http_status, description, translation)
