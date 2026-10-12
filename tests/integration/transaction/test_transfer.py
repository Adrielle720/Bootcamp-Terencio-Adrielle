# Casos da rota POST /accounts/{account_key}/transfers (RFC):
# - transferência entre contas ativas -> 201 com transfer_key, valor, tarifa e total; saldos mudam
# - qualquer titular ativo transfere, e o CPF pode ser de qualquer titular ativo do destino
# - origem não está ativa -> 409 QIT002026
# - dígito verificador do número não bate -> 422 QIT002040
# - destino não encontrado ou CPF não confere -> 404 QIT002041 (inclusive a conta da instituição)
# - destino não recebe (pendente ou cancelado) -> 409 QIT002042
# - mesma conta -> 422 QIT002043
# - saldo insuficiente para valor e tarifa -> 422 QIT002046
# - ledger: tarifa vai para a conta de receitas, depósito sai da conta de liquidação
# - os lançamentos de cada operação somam zero
# - número inexistente e CPF de não titular dão respostas idênticas
import requests

from utils.account_utils import abrir_conta, consultar_conta, criar_conta_ativa, depositar, transferir
from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES


def _saldo(conta):
    return consultar_conta(conta["account_key"], conta["master"]).json()["balance_cents"]


def _numero_com_dv_errado(numero):
    corpo, dv = numero.split("-")
    return f"{corpo}-{(int(dv) + 1) % 10}"


def _saldos_da_instituicao():
    resposta = requests.get(f"{SERVICES['transaction-service']}/internal/institution-balances", headers=HEADERS)
    resposta.raise_for_status()
    return resposta.json()


def test_transferencia_entre_contas_ativas_move_valor_e_tarifa():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()

    resposta = transferir(origem, destino, 10000)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert "transfer_key" in corpo
    assert (corpo["amount_cents"], corpo["fee_cents"], corpo["total_cents"]) == (10000, 200, 10200)
    assert _saldo(origem) == 39800
    assert _saldo(destino) == 10000


def test_membro_transfere_usando_o_cpf_de_um_membro_do_destino():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()

    resposta = transferir(origem, destino, 10000, quem=origem["convidado"],
                          cpf_destino=destino["convidado"]["document_number"])

    assert resposta.status_code == 201


def test_tarifas_vao_para_receitas_e_depositos_saem_da_liquidacao():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    antes = _saldos_da_instituicao()

    depositar(origem, 50000).raise_for_status()
    transferir(origem, destino, 10000).raise_for_status()

    depois = _saldos_da_instituicao()
    assert depois["fee_revenue_cents"] - antes["fee_revenue_cents"] == 200
    assert depois["settlement_cents"] - antes["settlement_cents"] == -50000


def test_origem_pendente_devolve_409_qit002026():
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": cadastrar_cliente()["phone"]}]).json()["account_key"]

    resposta = transferir({"account_key": account_key, "master": master}, criar_conta_ativa(), 1000)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"


def test_digito_verificador_errado_devolve_422_qit002040():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()

    resposta = transferir(origem, destino, 1000, numero_destino=_numero_com_dv_errado(destino["account_number"]))

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002040"


def test_cpf_que_nao_e_titular_do_destino_devolve_404_qit002041():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()

    resposta = transferir(origem, destino, 1000, cpf_destino=cadastrar_cliente()["document_number"])

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002041"


def test_conta_da_instituicao_como_destino_devolve_404_qit002041():
    origem = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()

    resposta = transferir(origem, origem, 1000, numero_destino="00000000-0")

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002041"


def test_destino_pendente_devolve_409_qit002042():
    origem = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()
    master = cadastrar_cliente()
    pendente = abrir_conta(master, [{"phone": cadastrar_cliente()["phone"]}]).json()

    resposta = transferir(origem, {**pendente, "master": master}, 1000)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002042"


def test_transferencia_para_a_propria_conta_devolve_422_qit002043():
    origem = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()

    resposta = transferir(origem, origem, 1000)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002043"


def test_transferencia_acima_do_saldo_devolve_422_qit002046():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 20000).raise_for_status()
    transferir(origem, destino, 15000).raise_for_status()

    saldos_antes = (_saldo(origem), _saldo(destino))

    resposta = transferir(origem, destino, 5000)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002046"
    assert (_saldo(origem), _saldo(destino)) == saldos_antes


def test_saldo_que_cobre_o_valor_mas_nao_a_tarifa_devolve_422_qit002046():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 10000).raise_for_status()

    resposta = transferir(origem, destino, 10000)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002046"


def _lancamentos(conta, transaction_key):
    resposta = requests.get(f"{SERVICES['statement-service']}/accounts/{conta['account_key']}/transactions/{transaction_key}",
                            params={"customer_key": conta["master"]["customer_key"]}, headers=HEADERS)
    return sum(lancamento["amount_cents"] for lancamento in resposta.json()["entries"])


def test_lancamentos_de_deposito_e_transferencia_somam_zero():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    antes = _saldos_da_instituicao()

    deposito = depositar(origem, 50000).json()
    depois_do_deposito = _saldos_da_instituicao()
    transferencia = transferir(origem, destino, 10000).json()
    depois_da_transferencia = _saldos_da_instituicao()

    liquidacao = depois_do_deposito["settlement_cents"] - antes["settlement_cents"]
    assert _lancamentos(origem, deposito["deposit_key"]) + liquidacao == 0
    receitas = depois_da_transferencia["fee_revenue_cents"] - depois_do_deposito["fee_revenue_cents"]
    debito = _lancamentos(origem, transferencia["transfer_key"])
    credito = _lancamentos(destino, transferencia["transfer_key"])
    assert (debito, credito, receitas) == (-10200, 10000, 200)
    assert debito + credito + receitas == 0


def test_numero_inexistente_e_cpf_de_nao_titular_dao_respostas_identicas():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()

    numero_inexistente = transferir(origem, destino, 1000, numero_destino="12345678-" + _dv("12345678"))
    cpf_de_fora = transferir(origem, destino, 1000, cpf_destino=cadastrar_cliente(aprovado=False)["document_number"])

    assert numero_inexistente.status_code == cpf_de_fora.status_code == 404
    assert numero_inexistente.json() == cpf_de_fora.json()


def _dv(corpo):
    total = sum(int(digito) * peso for digito, peso in zip(corpo, [2, 3, 4, 5, 6, 7, 8, 9]))
    resto = total % 11
    return str(0 if resto < 2 else 11 - resto)
