import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/account"
CUSTOMER_URL = f"{SERVICES['customer-service']}/customer"


def _criar_conta(master, convidado):
    resposta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )
    resposta.raise_for_status()
    return resposta.json()["account_key"]


def test_cliente_lista_seus_convites_pendentes():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)

    resposta = requests.get(f"{CUSTOMER_URL}/{convidado['customer_key']}/invitations", headers=HEADERS)

    assert resposta.status_code == 200
    convites = resposta.json()["data"]
    assert len(convites) == 1
    assert convites[0]["account_key"] == account_key
    assert "holder_key" in convites[0]


def _holder_key_do_convite(convidado, account_key):
    convites = requests.get(f"{CUSTOMER_URL}/{convidado['customer_key']}/invitations", headers=HEADERS).json()["data"]
    return next(convite["holder_key"] for convite in convites if convite["account_key"] == account_key)


def test_convidado_aceita_convite_e_recebe_200():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)
    holder_key = _holder_key_do_convite(convidado, account_key)

    resposta = requests.put(
        f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/accept",
        json={"customer_key": convidado["customer_key"]},
        headers=HEADERS,
    )

    assert resposta.status_code == 200


def test_aceitar_convite_ja_aceito_devolve_409_qit002031():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)
    holder_key = _holder_key_do_convite(convidado, account_key)
    requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/accept",
                 json={"customer_key": convidado["customer_key"]}, headers=HEADERS)

    resposta = requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/accept",
                            json={"customer_key": convidado["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002031"


def test_convite_de_outra_pessoa_devolve_404_qit002030():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    intruso = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)
    holder_key = _holder_key_do_convite(convidado, account_key)

    resposta = requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/accept",
                            json={"customer_key": intruso["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002030"


def test_recusa_do_ultimo_convite_cancela_conta_e_libera_o_master():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)
    holder_key = _holder_key_do_convite(convidado, account_key)

    recusa = requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/decline",
                          json={"customer_key": convidado["customer_key"]}, headers=HEADERS)
    nova_conta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Casa nova", "invite_phones": [cadastrar_cliente()["phone"]]},
        headers=HEADERS,
    )

    assert recusa.status_code == 200
    assert nova_conta.status_code == 201


def test_master_cancela_convite_pendente_e_recebe_200():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)
    holder_key = _holder_key_do_convite(convidado, account_key)

    resposta = requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/cancel",
                            json={"customer_key": master["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 200


def test_quem_nao_e_master_nao_cancela_convite_devolve_422_qit002028():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)
    holder_key = _holder_key_do_convite(convidado, account_key)

    resposta = requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/cancel",
                            json={"customer_key": convidado["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002028"


def test_cancelar_convite_ja_recusado_devolve_409_qit002031():
    master = cadastrar_cliente()
    recusante = cadastrar_cliente()
    outro_convidado = cadastrar_cliente()
    resposta_conta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302",
              "invite_phones": [recusante["phone"], outro_convidado["phone"]]},
        headers=HEADERS,
    )
    account_key = resposta_conta.json()["account_key"]
    holder_key = _holder_key_do_convite(recusante, account_key)
    requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/decline",
                 json={"customer_key": recusante["customer_key"]}, headers=HEADERS)

    resposta = requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/{holder_key}/cancel",
                            json={"customer_key": master["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002031"


def test_cancelar_convite_inexistente_devolve_404_qit002030():
    master = cadastrar_cliente()

    resposta = requests.put(f"{ACCOUNT_URL.replace('/account', '')}/invitation/00000000-0000-0000-0000-000000000000/cancel",
                            json={"customer_key": master["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002030"
