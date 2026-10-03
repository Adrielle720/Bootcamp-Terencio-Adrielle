import pytest
import requests

from utils.settings import MOCKSERVER_URL, SERVICES


@pytest.mark.parametrize("nome", SERVICES)
def test_servico_responde_health_check_com_204(nome):
    assert requests.get(f"{SERVICES[nome]}/health_check").status_code == 204


@pytest.mark.parametrize("nome", SERVICES)
def test_servico_se_identifica_na_raiz(nome):
    resposta = requests.get(f"{SERVICES[nome]}/")

    assert resposta.status_code == 200
    assert resposta.json()["service"] == nome


def test_mockserver_responde():
    assert requests.put(f"{MOCKSERVER_URL}/mockserver/status").status_code == 200
