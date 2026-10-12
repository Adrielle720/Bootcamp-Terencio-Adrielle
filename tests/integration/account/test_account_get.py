# Casos da rota GET /accounts/{account_key} (RFC):
# - titular ativo vê a conta, o saldo e os titulares com papel e status -> 200
# - quem não é titular ativo (inclusive convidado pendente) -> 404 QIT002020 (R8)
# - conta inexistente -> 404 QIT002020
from utils.account_utils import abrir_conta, consultar_conta, criar_conta_ativa, depositar
from utils.customer_utils import cadastrar_cliente


def test_titular_ativo_ve_conta_saldo_e_titulares():
    conta = criar_conta_ativa()
    depositar(conta, 50000).raise_for_status()

    resposta = consultar_conta(conta["account_key"], conta["convidado"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["account_key"] == conta["account_key"]
    assert corpo["account_number"] == conta["account_number"]
    assert corpo["status"] == "ACTIVE"
    assert corpo["balance_cents"] == 50000
    assert corpo["transfer_limit_cents"] is None
    papeis = sorted((titular["role"], titular["status"]) for titular in corpo["holders"])
    assert papeis == [("MASTER", "ACTIVE"), ("MEMBER", "ACTIVE")]
    assert all("account_holder_key" in titular for titular in corpo["holders"])


def test_convidado_pendente_nao_ve_a_conta_devolve_404_qit002020():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": convidado["phone"]}]).json()["account_key"]

    resposta = consultar_conta(account_key, convidado)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"


def test_conta_inexistente_devolve_404_qit002020():
    resposta = consultar_conta("00000000-0000-0000-0000-000000000000", cadastrar_cliente())

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"
