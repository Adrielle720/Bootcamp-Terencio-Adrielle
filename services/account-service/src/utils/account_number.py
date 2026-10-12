import random


def gerar_numero_da_conta() -> str:
    digitos = [random.randint(0, 9) for _ in range(8)]
    return "".join(str(digito) for digito in digitos) + "-" + str(_digito_verificador(digitos))


def _digito_verificador(digitos: list) -> int:
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    total = sum(digito * pesos[indice] for indice, digito in enumerate(digitos))
    resto = total % 11
    return 0 if resto < 2 else 11 - resto
