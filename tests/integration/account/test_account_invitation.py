# Casos da rota POST /account/{account_key}/invitation (RFC):
# - sétima vaga ocupada -> 409 QIT002025                              [em andamento]
# - só o master convida -> 422 QIT002028
# - conta cancelada ou encerrada -> 409 QIT002026
# - convidado já participa de outra conta -> 409 QIT002022
# - telefone sem cliente -> 404 QIT002023
# - conta inexistente -> 404 QIT002020
# - menor sem responsável adulto ativo -> 422 QIT002027
import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/account"


def _criar_conta_com_seis_vagas_ocupadas():
    master = cadastrar_cliente()
    convidados = [cadastrar_cliente() for _ in range(5)]

    resposta = requests.post(
        ACCOUNT_URL,
        json={
            "customer_key": master["customer_key"],
            "name": "Apartamento 302",
            "invite_phones": [convidado["phone"] for convidado in convidados],
        },
        headers=HEADERS,
    )
    resposta.raise_for_status()

    return master, resposta.json()["account_key"]


def test_setima_vaga_devolve_409_qit002025():
    master, account_key = _criar_conta_com_seis_vagas_ocupadas()
    extra = cadastrar_cliente()

    resposta = requests.post(
        f"{ACCOUNT_URL}/{account_key}/invitation",
        json={"customer_key": master["customer_key"], "phone": extra["phone"]},
        headers=HEADERS,
    )

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002025"
