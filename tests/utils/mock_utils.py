"""Expectations do Mockserver, que simula os dois serviços de fora.

- Birô: GET /bureau/cpf/{cpf} → {"status", "name_match", "birth_date_match"}, ou 404.
- Análise de documentos: POST /document-analysis/analyses → {"result", "pendency_reason"}.

Cada teste usa CPF e número de documento únicos, então cada expectation só
casa com o pedido daquele teste: nenhum teste depende de outro, e não é
preciso limpar o Mockserver entre eles.
"""
import json

import requests

from utils.settings import MOCKSERVER_URL


def _digits(document_number: str) -> str:
    return "".join(character for character in document_number if character.isdigit())


def _response(status: int, body: dict = None, delay_seconds: int = 0) -> dict:
    response = {"statusCode": status, "headers": {"Content-Type": ["application/json"]}}
    if body is not None:
        response["body"] = json.dumps(body)
    if delay_seconds:
        response["delay"] = {"timeUnit": "SECONDS", "value": delay_seconds}
    return response


def _expect(expectation_id: str, http_request: dict, http_response: dict) -> None:
    # O id fixo faz uma nova expectation para o mesmo CPF ou documento
    # substituir a anterior (sem ele, o Mockserver usaria a mais antiga).
    expectation = {"id": expectation_id, "httpRequest": http_request, "httpResponse": http_response,
                   "times": {"unlimited": True}}
    requests.put(f"{MOCKSERVER_URL}/mockserver/expectation", json=expectation).raise_for_status()


def mock_bureau(payload: dict, status: int = 200, bureau_status: str = "REGULAR", name_match: bool = True,
                birth_date_match: bool = True, delay_seconds: int = 0) -> None:
    body = None
    if status == 200:
        body = {"status": bureau_status, "name_match": name_match, "birth_date_match": birth_date_match}
    digits = _digits(payload["document_number"])
    _expect(f"bureau-{digits}", {"method": "GET", "path": f"/bureau/cpf/{digits}"},
            _response(status, body, delay_seconds))


def mock_bureau_ok(payload: dict) -> None:
    mock_bureau(payload)


def mock_bureau_unavailable(payload: dict) -> None:
    # O serviço espera no máximo 5 s; o birô "responde" depois disso.
    mock_bureau(payload, delay_seconds=7)


def mock_document(document_number: str, result: str = "APPROVED", pendency_reason: str = None,
                  delay_seconds: int = 0) -> None:
    _expect(
        f"document-{document_number}",
        {
            "method": "POST",
            "path": "/document-analysis/analyses",
            "body": {"type": "JSON", "json": {"document_number": document_number}, "matchType": "ONLY_MATCHING_FIELDS"},
        },
        _response(200, {"result": result, "pendency_reason": pendency_reason}, delay_seconds),
    )


def mock_document_approved(document_number: str) -> None:
    mock_document(document_number, "APPROVED")


def mock_document_pending(document_number: str, reason: str) -> None:
    mock_document(document_number, "PENDING", reason)


def mock_document_rejected(document_number: str) -> None:
    mock_document(document_number, "REJECTED")


def mock_document_unavailable(document_number: str) -> None:
    mock_document(document_number, delay_seconds=7)


def bureau_calls_at_most(payload: dict, times: int) -> bool:
    """Verify do Mockserver: o birô foi chamado no máximo `times` vezes para este CPF?"""
    verification = {
        "httpRequest": {"method": "GET", "path": f"/bureau/cpf/{_digits(payload['document_number'])}"},
        "times": {"atMost": times},
    }
    return requests.put(f"{MOCKSERVER_URL}/mockserver/verify", json=verification).status_code == 202
