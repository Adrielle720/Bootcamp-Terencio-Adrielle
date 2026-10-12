import time

import pytest
import requests

from utils.settings import MOCKSERVER_URL, SERVICES

STARTUP_TIMEOUT_SECONDS = 60


def _esperar(nome, verificacao):
    limite = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < limite:
        try:
            if verificacao():
                return
        except requests.ConnectionError:
            pass
        time.sleep(1)
    raise RuntimeError(f"{nome} não respondeu em {STARTUP_TIMEOUT_SECONDS}s. Rode: docker compose up -d")


@pytest.fixture(scope="session", autouse=True)
def servicos_no_ar():
    for nome, url in SERVICES.items():
        _esperar(nome, lambda url=url: requests.get(f"{url}/health_check", timeout=2).status_code == 204)
    _esperar("mockserver", lambda: requests.put(f"{MOCKSERVER_URL}/mockserver/status", timeout=2).status_code == 200)
