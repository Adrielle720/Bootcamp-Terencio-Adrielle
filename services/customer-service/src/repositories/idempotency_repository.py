from database import Context
from models import IdempotencyRecord


class IdempotencyRepository:
    """A resposta original de cada criação, guardada pela chave que o app mandou.

    O UNIQUE(scope, idempotency_key) é quem resolve a repetição simultânea:
    das duas gravações, só uma passa, e a outra devolve a resposta guardada.
    """

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get(self, scope: str, idempotency_key: str) -> IdempotencyRecord:
        return self.session.query(IdempotencyRecord).filter(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.idempotency_key == idempotency_key,
        ).first()

    def save(self, scope: str, idempotency_key: str, request_hash: str, response_status: int,
             response_body: dict) -> None:
        record = IdempotencyRecord()
        record.scope = scope
        record.idempotency_key = idempotency_key
        record.request_hash = request_hash
        record.response_status = response_status
        record.response_body = response_body
        self.session.add(record)
