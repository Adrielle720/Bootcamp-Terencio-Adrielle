import random
import uuid


def gerar_cpf() -> str:
    while True:
        digitos = [random.randint(0, 9) for _ in range(9)]
        if len(set(digitos)) == 1:
            continue
        digitos.append(_digito_verificador(digitos, 10))
        digitos.append(_digito_verificador(digitos, 11))
        numeros = "".join(str(d) for d in digitos)
        return f"{numeros[0:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:11]}"


def _digito_verificador(digitos: list, peso_inicial: int) -> int:
    total = sum(digito * (peso_inicial - indice) for indice, digito in enumerate(digitos))
    resto = total % 11
    return 0 if resto < 2 else 11 - resto


def gerar_telefone() -> str:
    return "11" + "".join(str(random.randint(0, 9)) for _ in range(9))


def gerar_email() -> str:
    return f"{uuid.uuid4().hex[:12]}@exemplo.com.br"


def customer_payload(**sobrescrever) -> dict:
    payload = {
        "document_number": gerar_cpf(),
        "name": "Maria da Silva",
        "mother_name": "Joana da Silva",
        "birthdate": "1990-05-17",
        "birth_city": "São Paulo",
        "residence_city": "São Paulo",
        "income_cents": 500000,
        "email": gerar_email(),
        "phone": gerar_telefone(),
    }
    payload.update(sobrescrever)
    return payload
