from controllers.base_controller import BaseController
from errors import IdempotencyConflict
from repositories import IdempotencyRepository


class IdempotentController(BaseController):
    """O que toda criação de dinheiro tem em comum: a chave de idempotência.

    A resposta original fica guardada em idempotency_records, no mesmo commit
    da operação. Repetir com o mesmo corpo devolve essa resposta sem gravar
    de novo; com outro corpo, é 422.
    """

    def __init__(self, class_name: str) -> None:
        super().__init__(class_name)
        self.idempotency_repository = IdempotencyRepository(self.context)

    def previous_response(self, scope: str, idempotency_key: str, body_hash: str):
        if idempotency_key is None:
            return None

        record = self.idempotency_repository.get(scope, idempotency_key)
        if record is None:
            return None
        if record.request_hash != body_hash:
            raise IdempotencyConflict(idempotency_key)
        return record.response_body

    def remember_response(self, scope: str, idempotency_key: str, body_hash: str, response: dict) -> None:
        if idempotency_key is not None:
            self.idempotency_repository.save(scope, idempotency_key, body_hash, 201, response)
