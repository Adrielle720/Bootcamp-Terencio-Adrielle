# Casos de convites: lista, aceite, recusa e cancelamento (RFC):
# - GET /account-holders lista os convites pela customer_key e pelos contatos da pessoa
# - quem não era cliente se cadastra com o contato convidado, vê o convite e aceita
# - aceite -> 200 e conta ACTIVE; aceitar de novo -> 409 QIT002031; convite de outra pessoa -> 404 QIT002030
# - aceite cancela os outros convites pendentes da pessoa
# - menor aceita -> papel MINOR, PENDING_GUARDIANSHIP, e não ativa a conta
# - recusa do último convite de conta pendente cancela a conta e libera o master
# - cancelamento pelo master: 200; não-master 422 QIT002028; já recusado 409 QIT002031; inexistente 404 QIT002030
from datetime import date

import requests

from utils.account_utils import (
    abrir_conta,
    acao_no_convite,
    aceitar_convite,
    chave_do_convite,
    consultar_conta,
    convites_pendentes,
    criar_conta_ativa,
)
from utils.customer_utils import cadastrar_cliente
from utils.generators import gerar_email, gerar_telefone
from utils.settings import HEADERS, SERVICES

CHAVE_INEXISTENTE = "00000000-0000-0000-0000-000000000000"


def _conta_pendente(convidados):
    master = cadastrar_cliente()
    resposta = abrir_conta(master, [{"phone": convidado["phone"]} for convidado in convidados])
    resposta.raise_for_status()
    return master, resposta.json()["account_key"]


def test_cliente_lista_seus_convites_pendentes():
    convidado = cadastrar_cliente()
    _, account_key = _conta_pendente([convidado])

    convites = convites_pendentes(convidado)

    assert len(convites) == 1
    assert convites[0]["account_key"] == account_key
    assert convites[0]["account_name"] == "Apartamento 302"
    assert "account_holder_key" in convites[0]


def test_lista_de_convites_de_cliente_inexistente_devolve_404_qit002010():
    resposta = requests.get(f"{SERVICES['account-service']}/account-holders",
                            params={"customer_key": CHAVE_INEXISTENTE}, headers=HEADERS)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002010"


def test_quem_nao_era_cliente_se_cadastra_ve_o_convite_e_aceita():
    master = cadastrar_cliente()
    email = gerar_email()
    account_key = abrir_conta(master, [{"email": email}]).json()["account_key"]

    novo_cliente = cadastrar_cliente(email=email)
    resposta = aceitar_convite(novo_cliente, account_key)

    assert resposta.status_code == 200
    assert consultar_conta(account_key, novo_cliente).json()["status"] == "ACTIVE"


def test_convidado_aceita_e_a_conta_fica_ativa():
    convidado = cadastrar_cliente()
    master, account_key = _conta_pendente([convidado])

    resposta = aceitar_convite(convidado, account_key)

    assert resposta.status_code == 200
    assert consultar_conta(account_key, master).json()["status"] == "ACTIVE"


def test_aceitar_convite_ja_aceito_devolve_409_qit002031():
    convidado = cadastrar_cliente()
    _, account_key = _conta_pendente([convidado])
    chave = chave_do_convite(convidado, account_key)
    acao_no_convite(chave, "accept", convidado).raise_for_status()

    resposta = acao_no_convite(chave, "accept", convidado)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002031"


def test_convite_de_outra_pessoa_devolve_404_qit002030():
    convidado = cadastrar_cliente()
    _, account_key = _conta_pendente([convidado])

    resposta = acao_no_convite(chave_do_convite(convidado, account_key), "accept", cadastrar_cliente())

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002030"


def test_aceite_cancela_os_outros_convites_e_a_conta_que_ficou_sem_convite():
    email, telefone = gerar_email(), gerar_telefone()
    primeira = abrir_conta(cadastrar_cliente(), [{"email": email}]).json()["account_key"]
    segundo_master = cadastrar_cliente()
    abrir_conta(segundo_master, [{"phone": telefone}]).raise_for_status()
    pessoa = cadastrar_cliente(email=email, phone=telefone)
    convites_antes = convites_pendentes(pessoa)

    resposta = aceitar_convite(pessoa, primeira)

    assert len(convites_antes) == 2
    assert resposta.status_code == 200
    assert convites_pendentes(pessoa) == []
    assert abrir_conta(segundo_master, [{"phone": gerar_telefone()}]).status_code == 201


def test_menor_aceita_e_fica_aguardando_guarda_sem_ativar_a_conta():
    nascimento = date.today().replace(year=date.today().year - 16).isoformat()
    menor = cadastrar_cliente(birth_date=nascimento)
    master, account_key = _conta_pendente([menor])

    resposta = aceitar_convite(menor, account_key)

    assert resposta.status_code == 200
    conta = consultar_conta(account_key, master).json()
    assert conta["status"] == "PENDING"
    assert ("MINOR", "PENDING_GUARDIANSHIP") in [(titular["role"], titular["status"]) for titular in conta["holders"]]


def test_recusa_do_ultimo_convite_cancela_conta_e_libera_o_master():
    convidado = cadastrar_cliente()
    master, account_key = _conta_pendente([convidado])

    recusa = acao_no_convite(chave_do_convite(convidado, account_key), "decline", convidado)
    nova_conta = abrir_conta(master, [{"phone": gerar_telefone()}])

    assert recusa.status_code == 200
    assert nova_conta.status_code == 201


def test_master_cancela_convite_pendente_e_recebe_200():
    convidado = cadastrar_cliente()
    master, account_key = _conta_pendente([convidado])

    resposta = acao_no_convite(chave_do_convite(convidado, account_key), "cancel", master)

    assert resposta.status_code == 200
    assert convites_pendentes(convidado) == []


def test_quem_nao_e_master_nao_cancela_convite_devolve_422_qit002028():
    conta = criar_conta_ativa()
    novo = cadastrar_cliente()
    requests.post(f"{SERVICES['account-service']}/accounts/{conta['account_key']}/holders",
                  json={"customer_key": conta["master"]["customer_key"], "phone": novo["phone"]},
                  headers=HEADERS).raise_for_status()

    resposta = acao_no_convite(chave_do_convite(novo, conta["account_key"]), "cancel", conta["convidado"])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002028"


def test_cancelar_convite_ja_recusado_devolve_409_qit002031():
    recusante = cadastrar_cliente()
    master, account_key = _conta_pendente([recusante, cadastrar_cliente()])
    chave = chave_do_convite(recusante, account_key)
    acao_no_convite(chave, "decline", recusante).raise_for_status()

    resposta = acao_no_convite(chave, "cancel", master)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002031"


def test_cancelar_convite_inexistente_devolve_404_qit002030():
    resposta = acao_no_convite(CHAVE_INEXISTENTE, "cancel", cadastrar_cliente())

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002030"
