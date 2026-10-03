# Casos de cancelamento pelo master (RFC):
# - master cancela conta pendente -> 200 e libera o master para abrir outra   [em andamento]
# - quem não é master tenta cancelar -> 422 QIT002028
# - conta já ativa não pode ser cancelada -> 409 QIT002026
# - conta inexistente -> 404 QIT002020
import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/account"


def _criar_conta(master, convidado):
    resposta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )
    resposta.raise_for_status()
    return resposta.json()["account_key"]


def test_master_cancela_conta_pendente_e_fica_livre_para_abrir_outra():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)

    cancelamento = requests.put(f"{ACCOUNT_URL}/{account_key}/cancel",
                                json={"customer_key": master["customer_key"]}, headers=HEADERS)
    nova_conta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Casa nova", "invite_phones": [cadastrar_cliente()["phone"]]},
        headers=HEADERS,
    )

    assert cancelamento.status_code == 200
    assert nova_conta.status_code == 201
