import json

import requests

from utils.settings import MOCKSERVER_URL


def mock_bureau_ok(payload: dict) -> None:
    digitos = "".join(caractere for caractere in payload["document_number"] if caractere.isdigit())
    expectation = {
        "httpRequest": {"method": "GET", "path": f"/bureau/cpf/{digitos}"},
        "httpResponse": {
            "statusCode": 200,
            "headers": {"Content-Type": ["application/json"]},
            "body": json.dumps({
                "document_status": "REGULAR",
                "name": payload["name"],
                "birthdate": payload["birthdate"],
            }),
        },
        "times": {"unlimited": True},
    }
    requests.put(f"{MOCKSERVER_URL}/mockserver/expectation", json=expectation).raise_for_status()
