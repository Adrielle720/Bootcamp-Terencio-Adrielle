# Concorrência do cadastro (RFC): dois cadastros do mesmo CPF ao mesmo tempo
# esbarram no UNIQUE, e o segundo recebe 409 QIT002003, nunca 500.
from concurrent.futures import ThreadPoolExecutor

import requests

from utils.generators import customer_payload, gerar_email, gerar_telefone
from utils.mock_utils import mock_bureau_ok
from utils.settings import HEADERS, SERVICES

SIMULTANEOS = 4


def test_cadastros_simultaneos_do_mesmo_cpf_criam_um_so_cliente():
    payload = customer_payload()
    mock_bureau_ok(payload)
    pedidos = [{**payload, "email": gerar_email(), "phone": gerar_telefone()} for _ in range(SIMULTANEOS)]

    with ThreadPoolExecutor(max_workers=SIMULTANEOS) as pool:
        respostas = list(pool.map(
            lambda corpo: requests.post(f"{SERVICES['customer-service']}/customers", json=corpo, headers=HEADERS),
            pedidos))

    assert sorted(resposta.status_code for resposta in respostas) == [201] + [409] * (SIMULTANEOS - 1)
    assert all(resposta.json()["code"] == "QIT002003" for resposta in respostas if resposta.status_code == 409)
