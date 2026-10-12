# Casos da guarda de menores, POST /accounts/{account_key}/guardianships e GET /guardianships/{key} (RFC):
# - menor aceita -> PENDING_GUARDIANSHIP (coberto em test_invitation_response)
# - mãe com RG e certidão do menor aprovados -> guarda APPROVED, menor ACTIVE, conta ACTIVE
# - mãe cujo nome não é o nome da mãe na certidão -> 422 QIT002036
# - avó sem documento de guarda -> 422 QIT002036; com documento -> APPROVED
# - documento ainda pendente -> guarda PENDING_DOCUMENTS e menor continua esperando
# - documento de guarda recusado na análise -> guarda REJECTED e convite do menor CANCELED
# - titular que não é menor -> 422 QIT002034
# - quem pede não é adulto -> 422 QIT002035
# - menor já com guarda aprovada -> 409 QIT002037
# - consulta da guarda -> 200; inexistente -> 404 QIT002038
import requests

from utils.account_utils import consultar_conta
from utils.customer_utils import cadastrar_cliente, enviar_documento, enviar_documento_aprovado, novo_numero_de_documento
from utils.minor_utils import aprovar_guarda_da_mae, chave_do_titular, conta_com_menor, pedir_guarda
from utils.mock_utils import mock_document_pending, mock_document_rejected
from utils.settings import HEADERS, SERVICES


def _situacao_do_menor(conta, menor=None):
    menor = menor or conta["menor"]
    titulares = consultar_conta(conta["account_key"], conta["master"]).json()["holders"]
    titular = next(t for t in titulares if t["account_holder_key"] == menor["holder_key"])
    return titular["role"], titular["status"]


def test_mae_com_documentos_aprovados_ativa_o_menor_e_a_conta():
    conta = conta_com_menor()

    resposta = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "MOTHER",
                            [conta["master"]["rg_key"], conta["menor"]["certidao_key"]])

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "APPROVED"
    assert all(documento["confirmed_at"] is not None for documento in corpo["documents"])
    assert _situacao_do_menor(conta) == ("MINOR", "ACTIVE")
    assert consultar_conta(conta["account_key"], conta["master"]).json()["status"] == "ACTIVE"


def test_mae_com_nome_diferente_do_da_certidao_devolve_422_qit002036():
    conta = conta_com_menor(nome_do_master="Outra Pessoa", mae_do_menor="Ana Souza Lima")

    resposta = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "MOTHER",
                            [conta["master"]["rg_key"], conta["menor"]["certidao_key"]])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002036"


def test_avo_sem_documento_de_guarda_devolve_422_qit002036_e_com_documento_e_aprovada():
    conta = conta_com_menor(nome_do_master="Maria Avó")
    documentos = [conta["master"]["rg_key"], conta["menor"]["certidao_key"]]

    sem_guarda = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "GRANDPARENT",
                              documentos)
    termo = enviar_documento_aprovado(conta["master"], "CUSTODY_ORDER")
    com_guarda = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "GRANDPARENT",
                              documentos + [termo])

    assert sem_guarda.status_code == 422
    assert sem_guarda.json()["code"] == "QIT002036"
    assert com_guarda.status_code == 201
    assert com_guarda.json()["status"] == "APPROVED"
    assert _situacao_do_menor(conta) == ("MINOR", "ACTIVE")


def test_documento_pendente_deixa_a_guarda_esperando_documentos():
    conta = conta_com_menor()
    numero = novo_numero_de_documento()
    mock_document_pending(numero, "ILLEGIBLE")
    certidao_ilegivel = enviar_documento(conta["menor"], "BIRTH_CERTIFICATE", numero).json()["document_key"]

    resposta = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "MOTHER",
                            [conta["master"]["rg_key"], certidao_ilegivel])

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "PENDING_DOCUMENTS"
    assert _situacao_do_menor(conta) == ("MINOR", "PENDING_GUARDIANSHIP")


def test_titular_que_nao_e_menor_devolve_422_qit002034():
    conta = conta_com_menor()
    chave_do_master = chave_do_titular(conta["account_key"], conta["master"], conta["master"])

    resposta = pedir_guarda(conta["account_key"], conta["master"], chave_do_master, "MOTHER",
                            [conta["master"]["rg_key"]])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002034"


def test_responsavel_menor_de_idade_devolve_422_qit002035():
    conta = conta_com_menor(menores=2)
    primeiro, segundo = conta["menores"]
    aprovar_guarda_da_mae(conta, primeiro)

    resposta = pedir_guarda(conta["account_key"], primeiro, segundo["holder_key"], "SIBLING",
                            [segundo["certidao_key"]])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002035"


def test_menor_com_guarda_aprovada_devolve_409_qit002037():
    conta = conta_com_menor()
    aprovar_guarda_da_mae(conta)

    resposta = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "MOTHER",
                            [conta["master"]["rg_key"], conta["menor"]["certidao_key"]])

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002037"


def test_consulta_da_guarda():
    conta = conta_com_menor()
    guarda = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "MOTHER",
                          [conta["master"]["rg_key"], conta["menor"]["certidao_key"]]).json()

    resposta = requests.get(f"{SERVICES['account-service']}/guardianships/{guarda['guardianship_key']}",
                            params={"customer_key": conta["menor"]["customer_key"]}, headers=HEADERS)
    estranho = requests.get(f"{SERVICES['account-service']}/guardianships/{guarda['guardianship_key']}",
                            params={"customer_key": cadastrar_cliente(aprovado=False)["customer_key"]},
                            headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.json()["kinship_degree"] == "MOTHER"
    assert estranho.status_code == 404
    assert estranho.json()["code"] == "QIT002038"


def test_documento_de_guarda_recusado_recusa_a_guarda_e_cancela_o_convite_do_menor():
    conta = conta_com_menor(nome_do_master="Maria Avó", outros_adultos=1)
    numero = novo_numero_de_documento()
    mock_document_rejected(numero)
    termo_recusado = enviar_documento(conta["master"], "CUSTODY_ORDER", numero).json()["document_key"]

    resposta = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "GRANDPARENT",
                            [conta["master"]["rg_key"], conta["menor"]["certidao_key"], termo_recusado])
    de_novo = pedir_guarda(conta["account_key"], conta["master"], conta["menor"]["holder_key"], "MOTHER",
                           [conta["master"]["rg_key"], conta["menor"]["certidao_key"]])

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "REJECTED"
    assert _situacao_do_menor(conta) == ("MINOR", "CANCELED")
    assert de_novo.status_code == 422
    assert de_novo.json()["code"] == "QIT002034"
