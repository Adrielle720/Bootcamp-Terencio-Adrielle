# Concorrência de convites (RFC, principal desafio do modelo):
# - grupos convidando a mesma pessoa ao mesmo tempo: exatamente uma conta criada, nenhuma 500
# - grupos convidando o mesmo contato (sem cliente) ao mesmo tempo: exatamente uma conta criada
# - convites disputando a última vaga: exatamente um passa
from concurrent.futures import ThreadPoolExecutor

import requests

from utils.account_utils import abrir_conta
from utils.customer_utils import cadastrar_cliente
from utils.generators import gerar_email, gerar_telefone
from utils.settings import HEADERS, SERVICES

SIMULTANEOS = 4


def _em_paralelo(funcao, itens):
    with ThreadPoolExecutor(max_workers=len(itens)) as pool:
        return sorted(resposta.status_code for resposta in pool.map(funcao, itens))


def test_grupos_simultaneos_nao_convidam_a_mesma_pessoa_duas_vezes():
    convidado = cadastrar_cliente()
    masters = [cadastrar_cliente() for _ in range(SIMULTANEOS)]

    codigos = _em_paralelo(lambda master: abrir_conta(master, [{"phone": convidado["phone"]}]), masters)

    assert codigos == [201] + [409] * (SIMULTANEOS - 1)


def test_grupos_simultaneos_nao_convidam_o_mesmo_contato_duas_vezes():
    email = gerar_email()
    masters = [cadastrar_cliente() for _ in range(SIMULTANEOS)]

    codigos = _em_paralelo(lambda master: abrir_conta(master, [{"email": email}]), masters)

    assert codigos == [201] + [409] * (SIMULTANEOS - 1)


def test_convites_disputando_a_ultima_vaga_so_um_passa():
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": gerar_telefone()} for _ in range(4)]).json()["account_key"]

    def _convidar(_):
        return requests.post(f"{SERVICES['account-service']}/accounts/{account_key}/holders",
                             json={"customer_key": master["customer_key"], "phone": gerar_telefone()},
                             headers=HEADERS)

    codigos = _em_paralelo(_convidar, list(range(SIMULTANEOS)))

    assert codigos == [201] + [409] * (SIMULTANEOS - 1)
