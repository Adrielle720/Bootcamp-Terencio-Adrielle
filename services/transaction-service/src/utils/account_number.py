ACCOUNT_NUMBER_WEIGHTS = [2, 3, 4, 5, 6, 7, 8, 9]


def check_digit(digits: list) -> int:
    total = sum(digit * ACCOUNT_NUMBER_WEIGHTS[index] for index, digit in enumerate(digits))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def has_valid_check_digit(account_number: str) -> bool:
    """Confere o dígito verificador sem consultar o banco.

    O schema já garantiu o formato "12345678-9". A conta é a mesma que o
    account-service usa ao gerar o número (utils/account_number.py de lá):
    um dígito errado na digitação é pego aqui, antes de qualquer consulta.
    """
    body, digit = account_number.split("-")
    return check_digit([int(character) for character in body]) == int(digit)
