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


class CustomerNotFound(QIException):
    code = "QIT002010"

    def __init__(self, customer_key) -> None:
        title = "Customer not found"
        http_status = 404
        description = f"There is no customer with the key {customer_key}."
        translation = "Cliente não encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentType(QIException):
    code = "QIT002011"

    def __init__(self, document_type) -> None:
        title = "Invalid document type"
        http_status = 422
        description = f"The document type {document_type} is not accepted."
        translation = "Tipo de documento não aceito."
        super().__init__(title, self.code, http_status, description, translation)


class ExpiredDocument(QIException):
    code = "QIT002012"

    def __init__(self, expiration_date) -> None:
        title = "Expired document"
        http_status = 422
        description = f"The document expired on {expiration_date}."
        translation = "O documento está vencido."
        super().__init__(title, self.code, http_status, description, translation)


class DocumentAnalysisUnavailable(QIException):
    code = "QIT002013"

    def __init__(self) -> None:
        title = "Document analysis unavailable"
        http_status = 502
        description = "The document analysis service did not respond in time."
        translation = "O serviço de análise de documentos não respondeu. Tente novamente."
        super().__init__(title, self.code, http_status, description, translation)


class IdempotencyConflict(QIException):
    code = "QIT002047"

    def __init__(self, idempotency_key) -> None:
        title = "Idempotency key reused with a different body"
        http_status = 422
        description = f"The Idempotency-Key {idempotency_key} was already used with a different request."
        translation = "Esta chave de idempotência já foi usada com outro pedido."
        super().__init__(title, self.code, http_status, description, translation)


class DocumentNotFound(QIException):
    code = "QIT002014"

    def __init__(self, document_key) -> None:
        title = "Document not found"
        http_status = 404
        description = f"There is no document with the key {document_key}."
        translation = "Documento não encontrado."
        super().__init__(title, self.code, http_status, description, translation)
