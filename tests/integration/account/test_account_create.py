# Casos da rota POST /accounts (RFC):
# - master adulto abre conta pendente com convidados por celular e e-mail -> 201 com account_key e account_number
# - convidado que ainda não é cliente -> 201, o convite guarda o contato
# - master inexistente -> 404 QIT002010
# - master com menos de 18 anos -> 422 QIT002021
# - master sem documentos aprovados -> 422 QIT002033
# - mesma Idempotency-Key -> mesma conta
# - master, ou convidado já cliente, com conta ou convite -> 409 QIT002022
# - contato que não é cliente e já tem convite pendente -> 409 QIT002032
# - convite a si mesmo ou repetido -> 422 QIT002024
# - convite sem e-mail nem celular -> 400 QIT000001
from datetime import date
import re
import uuid

import requests

from utils.account_utils import abrir_conta, consultar_conta
from utils.customer_utils import cadastrar_cliente
from utils.generators import gerar_email, gerar_telefone
from utils.settings import HEADERS, SERVICES

NUMERO_DA_CONTA = re.compile(r"^\d{8}-\d$")


def test_master_adulto_abre_conta_pendente_com_convidados():
    master = cadastrar_cliente()
    por_celular = cadastrar_cliente()
    por_email = cadastrar_cliente()

    resposta = abrir_conta(master, [{"phone": por_celular["phone"]}, {"email": por_email["email"]}])

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert NUMERO_DA_CONTA.match(corpo["account_number"])
    conta = consultar_conta(corpo["account_key"], master).json()
    assert conta["status"] == "PENDING"
    assert sorted(titular["status"] for titular in conta["holders"]) == ["ACTIVE", "INVITED", "INVITED"]


def test_convidado_que_ainda_nao_e_cliente_recebe_convite_pelo_contato():
    master = cadastrar_cliente()

    resposta = abrir_conta(master, [{"phone": gerar_telefone()}, {"email": gerar_email()}])

    assert resposta.status_code == 201


def test_master_inexistente_devolve_404_qit002010():
    fantasma = {"customer_key": "00000000-0000-0000-0000-000000000000"}

    resposta = abrir_conta(fantasma, [{"phone": gerar_telefone()}])

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002010"


def test_master_menor_de_18_anos_devolve_422_qit002021():
    nascimento = date.today().replace(year=date.today().year - 16).isoformat()
    master = cadastrar_cliente(birth_date=nascimento)

    resposta = abrir_conta(master, [{"phone": cadastrar_cliente()["phone"]}])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002021"


def test_convidado_ja_convidado_em_outra_conta_devolve_409_qit002022():
    convidado = cadastrar_cliente()
    abrir_conta(cadastrar_cliente(), [{"phone": convidado["phone"]}]).raise_for_status()

    resposta = abrir_conta(cadastrar_cliente(), [{"email": convidado["email"]}])

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002022"


def test_master_que_ja_tem_conta_devolve_409_qit002022():
    master = cadastrar_cliente()
    abrir_conta(master, [{"phone": gerar_telefone()}]).raise_for_status()

    resposta = abrir_conta(master, [{"phone": gerar_telefone()}])

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002022"


def test_contato_com_convite_pendente_devolve_409_qit002032():
    email = gerar_email()
    abrir_conta(cadastrar_cliente(), [{"email": email}]).raise_for_status()

    resposta = abrir_conta(cadastrar_cliente(), [{"email": email}])

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002032"


def test_master_convidando_a_si_mesmo_devolve_422_qit002024():
    master = cadastrar_cliente()

    resposta = abrir_conta(master, [{"phone": master["phone"]}])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002024"


def test_mesma_pessoa_convidada_duas_vezes_devolve_422_qit002024():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()

    resposta = abrir_conta(master, [{"phone": convidado["phone"]}, {"email": convidado["email"]}])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002024"


def test_convite_sem_email_nem_celular_devolve_400_qit000001():
    master = cadastrar_cliente()

    resposta = abrir_conta(master, [{}])

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_master_sem_documentos_aprovados_devolve_422_qit002033():
    master = cadastrar_cliente(aprovado=False)

    resposta = abrir_conta(master, [{"phone": gerar_telefone()}])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002033"


def test_mesma_chave_de_idempotencia_devolve_a_mesma_conta():
    master = cadastrar_cliente()
    corpo = {"customer_key": master["customer_key"], "name": "Casa", "invites": [{"phone": gerar_telefone()}]}
    headers = {**HEADERS, "Idempotency-Key": str(uuid.uuid4())}

    primeira = requests.post(f"{SERVICES['account-service']}/accounts", json=corpo, headers=headers)
    repetida = requests.post(f"{SERVICES['account-service']}/accounts", json=corpo, headers=headers)

    assert primeira.status_code == 201
    assert repetida.status_code == 201
    assert repetida.json() == primeira.json()
