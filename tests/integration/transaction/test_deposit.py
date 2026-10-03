# Casos da rota POST /account/{account_key}/deposit (RFC):
# - titular deposita em conta ativa -> 201 com transaction_key  [em andamento]
# - valor abaixo de R$ 10,00 -> 400 QIT000001
# - conta pendente, encerrada ou cancelada -> 409 QIT002026
# - conta inexistente ou quem pede não é titular ativo -> 404 QIT002020
import requests

from utils.account_utils import criar_conta_ativa
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['transaction-service']}/account"


def test_titular_deposita_em_conta_ativa_e_recebe_201():
    conta = criar_conta_ativa()

    resposta = requests.post(
        f"{URL}/{conta['account_key']}/deposit",
        json={"customer_key": conta["master"]["customer_key"], "amount_cents": 50000},
        headers=HEADERS,
    )

    assert resposta.status_code == 201
    assert "transaction_key" in resposta.json()
