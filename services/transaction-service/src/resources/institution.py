from fastapi import status
from fastapi.responses import JSONResponse

from controllers import InstitutionController


class InstitutionResource:
    """Rota interna, só de leitura: os saldos das contas da instituição, para auditar as tarifas."""

    def on_get_balances(self) -> JSONResponse:
        balances = InstitutionController().balances()

        return JSONResponse(content=balances, status_code=status.HTTP_200_OK)
