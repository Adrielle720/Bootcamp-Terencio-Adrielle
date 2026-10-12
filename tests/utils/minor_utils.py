from datetime import date

import requests

from utils.account_utils import abrir_conta, aceitar_convite, consultar_conta
from utils.customer_utils import cadastrar_cliente, enviar_documento_aprovado
from utils.settings import HEADERS, SERVICES

NOME_DA_MAE = "Ana Souza Lima"


def nascimento_de_menor(idade: int = 16) -> str:
    hoje = date.today()
    return hoje.replace(year=hoje.year - idade).isoformat()


def pedir_guarda(account_key: str, responsavel: dict, menor_holder_key: str, parentesco: str,
                 documentos: list) -> requests.Response:
    return requests.post(
        f"{SERVICES['account-service']}/accounts/{account_key}/guardianships",
        json={
            "customer_key": responsavel["customer_key"],
            "minor_account_holder_key": menor_holder_key,
            "kinship_degree": parentesco,
            "document_keys": documentos,
        },
        headers=HEADERS,
    )


def chave_do_titular(account_key: str, quem_pergunta: dict, cliente: dict) -> str:
    titulares = consultar_conta(account_key, quem_pergunta).json()["holders"]
    return next(t["account_holder_key"] for t in titulares if t["name"] == cliente["name"]
                and t.get("role") in ("MINOR", "MEMBER", "MASTER"))


def conta_com_menor(nome_do_master: str = NOME_DA_MAE, mae_do_menor: str = NOME_DA_MAE,
                    menores: int = 1, outros_adultos: int = 0) -> dict:
    """Master adulto + menor(es) que já aceitaram e esperam a guarda.

    Cada menor tem um nome próprio e a certidão de nascimento já aprovada.
    outros_adultos acrescenta adultos que também aceitam o convite.
    """
    master = cadastrar_cliente(name=nome_do_master)
    filhos = [
        cadastrar_cliente(name=f"Filho {indice} Souza", birth_date=nascimento_de_menor(), mother_name=mae_do_menor)
        for indice in range(menores)
    ]
    adultos = [cadastrar_cliente(name=f"Adulto {indice} Lima") for indice in range(outros_adultos)]
    conta = abrir_conta(master, [{"phone": pessoa["phone"]} for pessoa in filhos + adultos])
    conta.raise_for_status()
    account_key = conta.json()["account_key"]

    for adulto in adultos:
        aceitar_convite(adulto, account_key).raise_for_status()

    for filho in filhos:
        aceitar_convite(filho, account_key).raise_for_status()
        filho["certidao_key"] = enviar_documento_aprovado(filho, "BIRTH_CERTIFICATE")
        filho["holder_key"] = chave_do_titular(account_key, master, filho)

    return {
        "master": master,
        "menor": filhos[0],
        "menores": filhos,
        "account_key": account_key,
        "account_number": conta.json()["account_number"],
    }


def aprovar_guarda_da_mae(conta: dict, menor: dict = None) -> None:
    menor = menor or conta["menor"]
    pedir_guarda(conta["account_key"], conta["master"], menor["holder_key"], "MOTHER",
                 [conta["master"]["rg_key"], menor["certidao_key"]]).raise_for_status()
