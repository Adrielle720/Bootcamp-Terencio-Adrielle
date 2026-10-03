# Casos da rota POST /customer (RFC):
# - cadastro válido -> 201 com customer_key                      [em andamento]
# - dígitos do CPF errados -> 422 QIT002001
# - menos de 15 anos -> 422 QIT002002
# - CPF / e-mail / telefone repetido -> 409 (QIT002003/4/5)
# - birô: CPF inexistente / irregular / divergente -> 422 (QIT002006/7/8)
# - birô sem resposta -> 502 QIT002009
# - corpo fora do formato -> 400 QIT000001
import requests

from utils.generators import customer_payload
from utils.mock_utils import mock_bureau_ok
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['customer-service']}/customer"


def test_cadastro_valido_devolve_201_com_customer_key():
    payload = customer_payload()
    mock_bureau_ok(payload)

    resposta = requests.post(URL, json=payload, headers=HEADERS)

    assert resposta.status_code == 201
    assert "customer_key" in resposta.json()
