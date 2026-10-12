from abc import ABCMeta

from utils.logger import get_logger


class BaseController(metaclass=ABCMeta):
    """O que todo controller deste serviço tem em comum: o log.

    O statement-service não tem banco: ele monta o extrato perguntando ao
    account-service e ao transaction-service (composição de API). Por isso,
    diferente dos outros serviços, aqui não existe sessão nem commit.
    """

    def __init__(self, class_name: str) -> None:
        self.logger = get_logger(class_name)
