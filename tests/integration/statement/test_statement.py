# Casos do extrato, GET /accounts/{account_key}/transactions e /transactions/{transaction_key} (RFC):
# - depósito, transferência enviada e recebida, da mais recente para a mais antiga, com resumo
# - paginação: limit, page, is_last_page
# - filtros: tipo, sentido, titular e período
# - a soma dos itens bate com o saldo, e transferência recusada não aparece
# - start_date depois de end_date ou data impossível -> 400 QIT000001
# - quem não é titular ativo -> 404 QIT002020
# - limit acima de 100 ou parâmetro desconhecido -> 400 QIT000001
# - detalhe de uma operação com os lançamentos -> 200; operação de outra conta -> 404 QIT002050
from datetime import date, timedelta

import requests

from utils.account_utils import consultar_conta, criar_conta_ativa, depositar, transferir
from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['statement-service']}/accounts"


def _extrato(conta, quem=None, **filtros):
    params = {"customer_key": (quem or conta["master"])["customer_key"], **filtros}
    return requests.get(f"{URL}/{conta['account_key']}/transactions", params=params, headers=HEADERS)


def _detalhe(conta, transaction_key, quem=None):
    return requests.get(f"{URL}/{conta['account_key']}/transactions/{transaction_key}",
                        params={"customer_key": (quem or conta["master"])["customer_key"]}, headers=HEADERS)


def _conta_com_movimento():
    conta = criar_conta_ativa()
    outra = criar_conta_ativa()
    deposito = depositar(conta, 300000, quem=conta["convidado"]).json()
    depositar(outra, 300000).raise_for_status()
    enviada = transferir(conta, outra, 100000).json()
    recebida = transferir(outra, conta, 20000, quem=outra["convidado"],
                          cpf_destino=conta["convidado"]["document_number"]).json()
    return conta, outra, deposito, enviada, recebida


def test_extrato_mostra_as_operacoes_da_mais_recente_para_a_mais_antiga_com_resumo():
    conta, outra, deposito, enviada, recebida = _conta_com_movimento()

    resposta = _extrato(conta, quem=conta["convidado"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["summary"] == {
        "balance_cents": 300000 - 100000 - 900 + 20000,
        "total_in_cents": 320000,
        "total_out_cents": 100000,
        "total_fee_cents": 900,
    }
    assert (corpo["limit"], corpo["page"], corpo["is_last_page"]) == (10, 0, True)
    itens = corpo["data"]
    assert [item["transaction_key"] for item in itens] == [
        recebida["transfer_key"], enviada["transfer_key"], deposito["deposit_key"]]

    entrada, saida, deposito_item = itens
    assert (entrada["type"], entrada["direction"], entrada["fee_cents"]) == ("TRANSFER", "IN", 0)
    assert entrada["counterparty"]["account_number"] == outra["account_number"]
    assert entrada["made_by"]["name"] == outra["convidado"]["name"]
    assert (saida["type"], saida["direction"]) == ("TRANSFER", "OUT")
    assert (saida["amount_cents"], saida["fee_cents"], saida["total_cents"]) == (100000, 900, 100900)
    assert saida["counterparty"] == {"account_number": outra["account_number"], "name": outra["master"]["name"]}
    assert (deposito_item["type"], deposito_item["direction"], deposito_item["counterparty"]) == ("DEPOSIT", "IN", None)
    assert deposito_item["created_at"].endswith("-03:00")


def test_extrato_paginado():
    conta, _, deposito, enviada, recebida = _conta_com_movimento()

    primeira = _extrato(conta, limit=2, page=0).json()
    segunda = _extrato(conta, limit=2, page=1).json()

    assert [item["transaction_key"] for item in primeira["data"]] == [recebida["transfer_key"], enviada["transfer_key"]]
    assert primeira["is_last_page"] is False
    assert [item["transaction_key"] for item in segunda["data"]] == [deposito["deposit_key"]]
    assert segunda["is_last_page"] is True


def test_filtros_por_tipo_sentido_e_titular():
    conta, _, deposito, enviada, _ = _conta_com_movimento()
    titulares = consultar_conta(conta["account_key"], conta["master"]).json()["holders"]
    chave_do_convidado = next(t["account_holder_key"] for t in titulares if t["role"] == "MEMBER")

    so_depositos = _extrato(conta, type="DEPOSIT").json()
    so_saidas = _extrato(conta, direction="OUT").json()
    do_convidado = _extrato(conta, holder_key=chave_do_convidado).json()

    assert [item["transaction_key"] for item in so_depositos["data"]] == [deposito["deposit_key"]]
    assert so_depositos["summary"]["total_in_cents"] == 300000
    assert [item["transaction_key"] for item in so_saidas["data"]] == [enviada["transfer_key"]]
    assert so_saidas["summary"]["total_in_cents"] == 0
    assert [item["transaction_key"] for item in do_convidado["data"]] == [deposito["deposit_key"]]


def test_filtro_por_periodo():
    conta, *_ = _conta_com_movimento()
    amanha = (date.today() + timedelta(days=2)).isoformat()
    ontem = (date.today() - timedelta(days=2)).isoformat()

    futuro = _extrato(conta, start_date=amanha).json()
    janela = _extrato(conta, start_date=ontem, end_date=amanha).json()

    assert futuro["data"] == []
    assert len(janela["data"]) == 3


def test_quem_nao_e_titular_ativo_devolve_404_qit002020():
    conta = criar_conta_ativa()

    resposta = _extrato(conta, quem=cadastrar_cliente())

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"


def test_limit_acima_de_100_devolve_400_qit000001():
    resposta = _extrato(criar_conta_ativa(), limit=101)

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_parametro_desconhecido_devolve_400_qit000001():
    resposta = _extrato(criar_conta_ativa(), pagina=1)

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_detalhe_de_uma_transferencia_mostra_os_lancamentos_da_conta():
    conta, _, _, enviada, _ = _conta_com_movimento()

    resposta = _detalhe(conta, enviada["transfer_key"])

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["type"], corpo["direction"], corpo["total_cents"]) == ("TRANSFER", "OUT", 100900)
    lancamentos = sorted((lancamento["entry_type"], lancamento["amount_cents"]) for lancamento in corpo["entries"])
    assert lancamentos == [("FEE_DEBIT", -900), ("TRANSFER_DEBIT", -100000)]


def test_operacao_de_outra_conta_devolve_404_qit002050():
    conta = criar_conta_ativa()
    _, _, deposito_de_outra, _, _ = _conta_com_movimento()

    resposta = _detalhe(conta, deposito_de_outra["deposit_key"])

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002050"


def test_soma_dos_itens_bate_com_o_saldo_e_recusada_nao_aparece():
    conta, outra, *_ = _conta_com_movimento()
    recusada = transferir(conta, outra, 10000000)

    extrato = _extrato(conta, limit=100).json()

    assert recusada.status_code == 422
    assert len(extrato["data"]) == 3
    soma = sum(item["amount_cents"] if item["direction"] == "IN" else -item["total_cents"] for item in extrato["data"])
    assert soma == extrato["summary"]["balance_cents"]


def test_periodo_invertido_ou_data_impossivel_devolve_400_qit000001():
    conta = criar_conta_ativa()

    invertido = _extrato(conta, start_date="2026-10-10", end_date="2026-10-01")
    impossivel = _extrato(conta, start_date="2026-02-30")

    assert invertido.status_code == 400
    assert invertido.json()["code"] == "QIT000001"
    assert impossivel.status_code == 400
    assert impossivel.json()["code"] == "QIT000001"
