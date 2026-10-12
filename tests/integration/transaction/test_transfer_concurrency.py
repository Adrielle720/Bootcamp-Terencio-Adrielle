# Concorrência da transferência (RFC):
# - transferências simultâneas que juntas passam do saldo: exatamente uma aceita, nenhuma 500
# - mesma chave simultânea: uma única transação, todas as respostas 201 com a mesma chave
# - transferências cruzadas A->B e B->A ao mesmo tempo terminam sem deadlock
import uuid
from concurrent.futures import ThreadPoolExecutor

from utils.account_utils import criar_conta_ativa, depositar, transferir

SIMULTANEAS = 4


def test_transferencias_simultaneas_nao_passam_do_saldo_e_nunca_devolvem_500():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 20000).raise_for_status()

    with ThreadPoolExecutor(max_workers=SIMULTANEAS) as pool:
        respostas = list(pool.map(lambda _: transferir(origem, destino, 15000), range(SIMULTANEAS)))

    codigos = sorted(resposta.status_code for resposta in respostas)
    assert codigos == [201] + [422] * (SIMULTANEAS - 1)


def test_mesma_chave_simultanea_gera_uma_unica_transacao():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 50000).raise_for_status()
    chave = str(uuid.uuid4())

    with ThreadPoolExecutor(max_workers=SIMULTANEAS) as pool:
        respostas = list(pool.map(lambda _: transferir(origem, destino, 15000, chave=chave), range(SIMULTANEAS)))

    assert all(resposta.status_code == 201 for resposta in respostas)
    assert len({resposta.json()["transfer_key"] for resposta in respostas}) == 1


def test_transferencias_cruzadas_simultaneas_terminam_sem_deadlock():
    conta_a = criar_conta_ativa()
    conta_b = criar_conta_ativa()
    depositar(conta_a, 100000).raise_for_status()
    depositar(conta_b, 100000).raise_for_status()
    pares = [(conta_a, conta_b), (conta_b, conta_a)] * SIMULTANEAS

    with ThreadPoolExecutor(max_workers=len(pares)) as pool:
        respostas = list(pool.map(lambda par: transferir(par[0], par[1], 1000), pares))

    assert all(resposta.status_code == 201 for resposta in respostas)
