# Casos da rota GET /customers/{customer_key} (RFC):
# - cliente cadastrado -> 200 com os dados do cadastro
# - cliente inexistente -> 404 QIT002010
import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['customer-service']}/customers"


def test_cliente_cadastrado_devolve_200_com_os_dados():
    cliente = cadastrar_cliente()

    resposta = requests.get(f"{URL}/{cliente['customer_key']}", headers=HEADERS)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["customer_key"] == cliente["customer_key"]
    assert corpo["document_number"] == cliente["document_number"]
    assert corpo["name"] == cliente["name"]
    assert corpo["birth_date"] == cliente["birth_date"]
    assert corpo["email"] == cliente["email"]
    assert corpo["phone"] == cliente["phone"]
    assert "id" not in corpo


def test_cliente_inexistente_devolve_404_qit002010():
    resposta = requests.get(f"{URL}/00000000-0000-0000-0000-000000000000", headers=HEADERS)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002010"
