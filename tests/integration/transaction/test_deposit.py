# Casos da rota POST /accounts/{account_key}/deposits (RFC):
# - titular deposita em conta ativa -> 201 com deposit_key, e o saldo sobe
# - mesma Idempotency-Key -> mesma resposta, crédito uma vez só
# - valor abaixo de R$ 10,00 -> 400 QIT000001
# - conta pendente, encerrada ou cancelada -> 409 QIT002026
# - conta inexistente ou quem pede não é titular ativo -> 404 QIT002020
import uuid

from utils.account_utils import abrir_conta, consultar_conta, criar_conta_ativa, depositar
from utils.customer_utils import cadastrar_cliente


def _saldo(conta):
    return consultar_conta(conta["account_key"], conta["master"]).json()["balance_cents"]


def test_titular_deposita_em_conta_ativa_e_o_saldo_sobe():
    conta = criar_conta_ativa()

    resposta = depositar(conta, 50000, quem=conta["convidado"])

    assert resposta.status_code == 201
    assert "deposit_key" in resposta.json()
    assert resposta.json()["amount_cents"] == 50000
    assert _saldo(conta) == 50000


def test_mesma_chave_devolve_o_mesmo_deposito_e_credita_uma_vez():
    conta = criar_conta_ativa()
    chave = str(uuid.uuid4())

    primeira = depositar(conta, 50000, chave=chave)
    repetida = depositar(conta, 50000, chave=chave)

    assert primeira.status_code == 201
    assert repetida.status_code == 201
    assert repetida.json()["deposit_key"] == primeira.json()["deposit_key"]
    assert _saldo(conta) == 50000


def test_mesma_chave_com_outro_valor_devolve_422_qit002047():
    conta = criar_conta_ativa()
    chave = str(uuid.uuid4())
    depositar(conta, 50000, chave=chave).raise_for_status()

    resposta = depositar(conta, 60000, chave=chave)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002047"


def test_deposito_abaixo_de_10_reais_devolve_400_qit000001():
    resposta = depositar(criar_conta_ativa(), 999)

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_deposito_em_conta_pendente_devolve_409_qit002026():
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": cadastrar_cliente()["phone"]}]).json()["account_key"]

    resposta = depositar({"account_key": account_key, "master": master}, 50000)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"


def test_quem_nao_e_titular_ativo_devolve_404_qit002020():
    resposta = depositar(criar_conta_ativa(), 50000, quem=cadastrar_cliente())

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"


def test_conta_da_instituicao_nao_recebe_deposito_de_cliente_devolve_404_qit002020():
    instituicao = {"account_key": "00000000-0000-0000-0000-000000000001", "master": cadastrar_cliente()}

    resposta = depositar(instituicao, 50000)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"
