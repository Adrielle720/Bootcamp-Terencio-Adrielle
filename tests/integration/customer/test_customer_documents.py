# Casos da esteira de documentos, POST e GET /customers/{customer_key}/documents (RFC):
# - documento aprovado -> 201 APPROVED; RG + comprovante aprovados -> cliente APPROVED
# - documento com pendência -> PENDING com o motivo visível; cliente continua PENDING_DOCUMENTS
# - documento novo aprovado do mesmo tipo resolve a pendência anterior
# - documento reprovado -> cliente REJECTED
# - tipo inválido -> 422 QIT002011; vencido -> 422 QIT002012 (antes da análise)
# - análise sem resposta -> 502 QIT002013
# - cliente inexistente -> 404 QIT002010
import requests

from utils.customer_utils import (
    cadastrar_cliente,
    consultar_cliente,
    enviar_documento,
    enviar_documento_aprovado,
    novo_numero_de_documento,
)
from utils.mock_utils import (
    mock_document_approved,
    mock_document_pending,
    mock_document_rejected,
    mock_document_unavailable,
)
from utils.settings import HEADERS, SERVICES


def _status(cliente):
    return consultar_cliente(cliente).json()["status"]


def test_documento_aprovado_e_cliente_aprovado_com_rg_e_comprovante():
    cliente = cadastrar_cliente(aprovado=False)
    numero = novo_numero_de_documento()
    mock_document_approved(numero)

    resposta = enviar_documento(cliente, "RG", numero)
    status_com_um_documento = _status(cliente)
    enviar_documento_aprovado(cliente, "PROOF_OF_ADDRESS")

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "APPROVED"
    assert "document_key" in resposta.json()
    assert status_com_um_documento == "PENDING_DOCUMENTS"
    assert _status(cliente) == "APPROVED"


def test_cnh_tambem_vale_como_documento_de_identidade():
    cliente = cadastrar_cliente(aprovado=False)

    enviar_documento_aprovado(cliente, "CNH")
    enviar_documento_aprovado(cliente, "PROOF_OF_ADDRESS")

    assert _status(cliente) == "APPROVED"


def test_documento_com_pendencia_mostra_o_motivo_e_novo_documento_resolve():
    cliente = cadastrar_cliente(aprovado=False)
    ilegivel = novo_numero_de_documento()
    mock_document_pending(ilegivel, "ILLEGIBLE")

    pendente = enviar_documento(cliente, "RG", ilegivel)
    cliente_com_pendencia = consultar_cliente(cliente).json()
    enviar_documento_aprovado(cliente, "RG")
    enviar_documento_aprovado(cliente, "PROOF_OF_ADDRESS")
    cliente_depois = consultar_cliente(cliente).json()

    assert pendente.status_code == 201
    assert pendente.json()["status"] == "PENDING"
    assert pendente.json()["pendencies"][0]["reason"] == "ILLEGIBLE"
    assert cliente_com_pendencia["status"] == "PENDING_DOCUMENTS"
    assert [p["reason"] for p in cliente_com_pendencia["pendencies"]] == ["ILLEGIBLE"]
    assert cliente_depois["status"] == "APPROVED"
    assert cliente_depois["pendencies"] == []

    documentos = requests.get(f"{SERVICES['customer-service']}/customers/{cliente['customer_key']}/documents",
                              headers=HEADERS).json()["data"]
    primeiro = next(d for d in documentos if d["document_number"] == ilegivel)
    assert primeiro["status"] == "PENDING"
    assert primeiro["pendencies"] == []


def test_documento_reprovado_deixa_o_cliente_rejeitado():
    cliente = cadastrar_cliente(aprovado=False)
    numero = novo_numero_de_documento()
    mock_document_rejected(numero)

    resposta = enviar_documento(cliente, "RG", numero)

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "REJECTED"
    assert _status(cliente) == "REJECTED"


def test_tipo_de_documento_invalido_devolve_422_qit002011():
    resposta = enviar_documento(cadastrar_cliente(aprovado=False), "PASSAPORTE")

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002011"


def test_documento_vencido_devolve_422_qit002012():
    resposta = enviar_documento(cadastrar_cliente(aprovado=False), "RG", validade="2020-01-01")

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002012"


def test_analise_sem_resposta_devolve_502_qit002013():
    cliente = cadastrar_cliente(aprovado=False)
    numero = novo_numero_de_documento()
    mock_document_unavailable(numero)

    resposta = enviar_documento(cliente, "RG", numero)

    assert resposta.status_code == 502
    assert resposta.json()["code"] == "QIT002013"


def test_documento_de_cliente_inexistente_devolve_404_qit002010():
    resposta = enviar_documento({"customer_key": "00000000-0000-0000-0000-000000000000"}, "RG")

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002010"
