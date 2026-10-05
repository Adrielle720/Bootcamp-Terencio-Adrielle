import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES


def criar_conta_com_titulares(total: int) -> dict:
    master = cadastrar_cliente()
    convidados = [cadastrar_cliente() for _ in range(total - 1)]

    conta = requests.post(
        f"{SERVICES['account-service']}/account",
        json={
            "customer_key": master["customer_key"],
            "name": "Apartamento 302",
            "invite_phones": [convidado["phone"] for convidado in convidados],
        },
        headers=HEADERS,
    )
    conta.raise_for_status()
    account_key = conta.json()["account_key"]

    for convidado in convidados:
        convites = requests.get(f"{SERVICES['customer-service']}/customer/{convidado['customer_key']}/invitations",
                                headers=HEADERS).json()["data"]
        holder_key = next(convite["holder_key"] for convite in convites if convite["account_key"] == account_key)
        requests.put(f"{SERVICES['account-service']}/invitation/{holder_key}/accept",
                     json={"customer_key": convidado["customer_key"]}, headers=HEADERS).raise_for_status()

    return {
        "master": master,
        "convidados": convidados,
        "convidado": convidados[0] if convidados else None,
        "account_key": account_key,
        "account_number": conta.json()["account_number"],
    }


def criar_conta_ativa() -> dict:
    return criar_conta_com_titulares(2)
