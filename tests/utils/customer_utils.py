import uuid

import requests

from utils.generators import customer_payload
from utils.mock_utils import mock_bureau_ok, mock_document_approved
from utils.settings import HEADERS, SERVICES

CUSTOMER_URL = f"{SERVICES['customer-service']}/customers"


def novo_numero_de_documento() -> str:
    return uuid.uuid4().hex[:12].upper()


def enviar_documento(cliente: dict, tipo: str, numero: str = None, validade: str = "2035-01-01") -> requests.Response:
    return requests.post(
        f"{CUSTOMER_URL}/{cliente['customer_key']}/documents",
        json={"document_type": tipo, "document_number": numero or novo_numero_de_documento(),
              "expiration_date": validade},
        headers=HEADERS,
    )


def enviar_documento_aprovado(cliente: dict, tipo: str) -> str:
    numero = novo_numero_de_documento()
    mock_document_approved(numero)
    resposta = enviar_documento(cliente, tipo, numero)
    resposta.raise_for_status()
    return resposta.json()["document_key"]


def cadastrar_cliente(aprovado: bool = True, **sobrescrever) -> dict:
    """Cadastra pela API. Aprovado (o padrão) também envia RG e comprovante aprovados.

    Devolve o corpo do cadastro com a customer_key e, se aprovado, a
    document_key do RG em "rg_key" (útil para a guarda de menores).
    """
    payload = customer_payload(**sobrescrever)
    mock_bureau_ok(payload)

    resposta = requests.post(CUSTOMER_URL, json=payload, headers=HEADERS)
    resposta.raise_for_status()
    cliente = {**payload, "customer_key": resposta.json()["customer_key"]}

    if aprovado:
        cliente["rg_key"] = enviar_documento_aprovado(cliente, "RG")
        enviar_documento_aprovado(cliente, "PROOF_OF_ADDRESS")

    return cliente


def consultar_cliente(cliente: dict) -> requests.Response:
    return requests.get(f"{CUSTOMER_URL}/{cliente['customer_key']}", headers=HEADERS)
