from concurrent.futures import ThreadPoolExecutor

import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/account"
SIMULTANEOS = 4


def test_grupos_simultaneos_nao_convidam_a_mesma_pessoa_duas_vezes():
    convidado = cadastrar_cliente()
    masters = [cadastrar_cliente() for _ in range(SIMULTANEOS)]

    def _abrir_conta(master):
        return requests.post(
            ACCOUNT_URL,
            json={"customer_key": master["customer_key"], "name": "Grupo", "invite_phones": [convidado["phone"]]},
            headers=HEADERS,
        )

    with ThreadPoolExecutor(max_workers=SIMULTANEOS) as pool:
        respostas = list(pool.map(_abrir_conta, masters))

    codigos = sorted(resposta.status_code for resposta in respostas)
    assert codigos == [201] + [409] * (SIMULTANEOS - 1)
