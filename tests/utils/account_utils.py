import uuid

import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = SERVICES["account-service"]
TRANSACTION_URL = SERVICES["transaction-service"]


def abrir_conta(master: dict, convites: list, nome: str = "Apartamento 302") -> requests.Response:
    return requests.post(
        f"{ACCOUNT_URL}/accounts",
        json={"customer_key": master["customer_key"], "name": nome, "invites": convites},
        headers=HEADERS,
    )


def convites_pendentes(cliente: dict) -> list:
    resposta = requests.get(
        f"{ACCOUNT_URL}/account-holders",
        params={"customer_key": cliente["customer_key"], "status": "INVITED"},
        headers=HEADERS,
    )
    resposta.raise_for_status()
    return resposta.json()["data"]


def chave_do_convite(cliente: dict, account_key: str) -> str:
    return next(convite["account_holder_key"] for convite in convites_pendentes(cliente)
                if convite["account_key"] == account_key)


def acao_no_convite(account_holder_key: str, acao: str, cliente: dict) -> requests.Response:
    return requests.put(
        f"{ACCOUNT_URL}/account-holders/{account_holder_key}/{acao}",
        json={"customer_key": cliente["customer_key"]},
        headers=HEADERS,
    )


def aceitar_convite(cliente: dict, account_key: str) -> requests.Response:
    return acao_no_convite(chave_do_convite(cliente, account_key), "accept", cliente)


def consultar_conta(account_key: str, cliente: dict) -> requests.Response:
    return requests.get(f"{ACCOUNT_URL}/accounts/{account_key}",
                        params={"customer_key": cliente["customer_key"]}, headers=HEADERS)


def criar_conta_com_titulares(total: int) -> dict:
    master = cadastrar_cliente()
    convidados = [cadastrar_cliente() for _ in range(total - 1)]

    conta = abrir_conta(master, [{"phone": convidado["phone"]} for convidado in convidados])
    conta.raise_for_status()
    account_key = conta.json()["account_key"]

    for convidado in convidados:
        aceitar_convite(convidado, account_key).raise_for_status()

    return {
        "master": master,
        "convidados": convidados,
        "convidado": convidados[0] if convidados else None,
        "account_key": account_key,
        "account_number": conta.json()["account_number"],
    }


def criar_conta_ativa() -> dict:
    return criar_conta_com_titulares(2)


def depositar(conta: dict, valor: int, quem: dict = None, chave: str = None) -> requests.Response:
    headers = dict(HEADERS)
    if chave is not None:
        headers["Idempotency-Key"] = chave
    return requests.post(
        f"{TRANSACTION_URL}/accounts/{conta['account_key']}/deposits",
        json={"customer_key": (quem or conta["master"])["customer_key"], "amount_cents": valor},
        headers=headers,
    )


def transferir(origem: dict, destino: dict, valor: int, quem: dict = None, chave: str = None,
               cpf_destino: str = None, numero_destino: str = None) -> requests.Response:
    return requests.post(
        f"{TRANSACTION_URL}/accounts/{origem['account_key']}/transfers",
        json={
            "customer_key": (quem or origem["master"])["customer_key"],
            "amount_cents": valor,
            "destination_account_number": numero_destino or destino["account_number"],
            "destination_document_number": cpf_destino or destino["master"]["document_number"],
        },
        headers={**HEADERS, "Idempotency-Key": chave or str(uuid.uuid4())},
    )
