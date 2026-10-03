import json

import requests

from utils.settings import MOCKSERVER_URL


def mock_bureau(payload: dict, status: int = 200, document_status: str = "REGULAR",
                name: str = None, birthdate: str = None, delay_seconds: int = 0) -> None:
    digitos = "".join(caractere for caractere in payload["document_number"] if caractere.isdigit())
    resposta = {"statusCode": status, "headers": {"Content-Type": ["application/json"]}}

    if status == 200:
        resposta["body"] = json.dumps({
            "document_status": document_status,
            "name": name or payload["name"],
            "birthdate": birthdate or payload["birthdate"],
        })
    if delay_seconds:
        resposta["delay"] = {"timeUnit": "SECONDS", "value": delay_seconds}

    expectation = {
        "httpRequest": {"method": "GET", "path": f"/bureau/cpf/{digitos}"},
        "httpResponse": resposta,
        "times": {"unlimited": True},
    }
    requests.put(f"{MOCKSERVER_URL}/mockserver/expectation", json=expectation).raise_for_status()


def mock_bureau_ok(payload: dict) -> None:
    mock_bureau(payload)
