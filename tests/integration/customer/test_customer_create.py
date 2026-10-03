# Casos da rota POST /customer (RFC):
# - cadastro válido -> 201 com customer_key                      [feito]
# - dígitos do CPF errados -> 422 QIT002001                       [em andamento]
# - menos de 15 anos -> 422 QIT002002                              [em andamento]
# - CPF / e-mail / telefone repetido -> 409 (QIT002003/4/5)       [CPF feito; e-mail em andamento]
# - birô: CPF inexistente / irregular / divergente -> 422 (QIT002006/7/8)  [inexistente feito; irregular em andamento]
# - birô sem resposta -> 502 QIT002009
# - corpo fora do formato -> 400 QIT000001
from datetime import date

import requests

from utils.generators import customer_payload
from utils.mock_utils import mock_bureau, mock_bureau_ok
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['customer-service']}/customer"


def test_cadastro_valido_devolve_201_com_customer_key():
    payload = customer_payload()
    mock_bureau_ok(payload)

    resposta = requests.post(URL, json=payload, headers=HEADERS)

    assert resposta.status_code == 201
    assert "customer_key" in resposta.json()


def test_cpf_com_digitos_verificadores_errados_devolve_422_qit002001():
    payload = customer_payload()
    digitos = list(payload["document_number"])
    digitos[-1] = "0" if digitos[-1] != "0" else "1"
    payload["document_number"] = "".join(digitos)

    resposta = requests.post(URL, json=payload, headers=HEADERS)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002001"


def test_menor_de_15_anos_devolve_422_qit002002():
    nascimento_recente = date.today().replace(year=date.today().year - 10).isoformat()
    payload = customer_payload(birthdate=nascimento_recente)

    resposta = requests.post(URL, json=payload, headers=HEADERS)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002002"


def test_cpf_ja_cadastrado_devolve_409_qit002003():
    payload = customer_payload()
    mock_bureau_ok(payload)
    requests.post(URL, json=payload, headers=HEADERS)

    resposta = requests.post(URL, json=customer_payload(document_number=payload["document_number"]), headers=HEADERS)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002003"


def test_email_ja_cadastrado_devolve_409_qit002004():
    payload = customer_payload()
    mock_bureau_ok(payload)
    requests.post(URL, json=payload, headers=HEADERS)

    resposta = requests.post(URL, json=customer_payload(email=payload["email"]), headers=HEADERS)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002004"


def test_telefone_ja_cadastrado_devolve_409_qit002005():
    payload = customer_payload()
    mock_bureau_ok(payload)
    requests.post(URL, json=payload, headers=HEADERS)

    resposta = requests.post(URL, json=customer_payload(phone=payload["phone"]), headers=HEADERS)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002005"


def test_cpf_inexistente_no_bureau_devolve_422_qit002006():
    payload = customer_payload()
    mock_bureau(payload, status=404)

    resposta = requests.post(URL, json=payload, headers=HEADERS)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002006"


def test_cpf_irregular_no_bureau_devolve_422_qit002007():
    payload = customer_payload()
    mock_bureau(payload, document_status="IRREGULAR")

    resposta = requests.post(URL, json=payload, headers=HEADERS)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002007"
