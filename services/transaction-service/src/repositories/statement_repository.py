from sqlalchemy import text

from database import Context

# Cada operação da conta vira uma linha: o depósito, a transferência que
# saiu e a que entrou. O extrato é uma consulta sobre o que foi gravado,
# nunca uma tabela própria. Tentativa recusada não grava nada, então não
# tem como aparecer aqui.
#
# created_at é gravado em UTC; "AT TIME ZONE 'UTC'" o transforma num
# instante, que o Postgres devolve no fuso da transação (São Paulo, ver
# _use_sao_paulo_time). O dia dos filtros de período sai do mesmo fuso.
ITEMS_SQL = """
    SELECT d.deposit_key AS transaction_key, 'DEPOSIT' AS type, 'IN' AS direction,
           d.amount_cents, 0 AS fee_cents, d.created_at AT TIME ZONE 'UTC' AS created_at,
           d.depositor_customer_key AS made_by_customer_key, d.depositor_name AS made_by_name,
           NULL AS counterparty_account_number, NULL AS counterparty_name
      FROM deposits d
     WHERE d.account_key = :account_key
    UNION ALL
    SELECT t.transfer_key, 'TRANSFER', 'OUT',
           t.amount_cents, t.fee_cents, t.created_at AT TIME ZONE 'UTC',
           t.requester_customer_key, t.requester_name,
           t.destination_account_number, t.verified_holder_name
      FROM transfers t
     WHERE t.origin_account_key = :account_key
    UNION ALL
    SELECT t.transfer_key, 'TRANSFER', 'IN',
           t.amount_cents, 0, t.created_at AT TIME ZONE 'UTC',
           t.requester_customer_key, t.requester_name,
           t.origin_account_number, t.requester_name
      FROM transfers t
     WHERE t.destination_account_key = :account_key
"""

FILTERS = {
    "type": "items.type = :type",
    "direction": "items.direction = :direction",
    "start_date": "items.created_at::date >= :start_date",
    "end_date": "items.created_at::date <= :end_date",
    # Quem fez a operação é um titular desta conta: uma transferência que
    # entrou foi feita por alguém de outra conta, e nunca casa com o filtro.
    "made_by": "items.made_by_customer_key = :made_by AND NOT (items.type = 'TRANSFER' AND items.direction = 'IN')",
}


class StatementRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def list_items(self, account_key: str, filters: dict, limit: int, offset: int) -> list:
        """Uma linha a mais do que a página: se ela vier, não é a última página."""
        self._use_sao_paulo_time()
        where, params = self._where(account_key, filters)
        rows = self.session.execute(text(
            f"SELECT * FROM ({ITEMS_SQL}) items {where} "
            "ORDER BY items.created_at DESC, items.transaction_key DESC LIMIT :limit OFFSET :offset"
        ), {**params, "limit": limit + 1, "offset": offset}).mappings().all()
        return [dict(row) for row in rows]

    def summarize(self, account_key: str, filters: dict) -> dict:
        self._use_sao_paulo_time()
        where, params = self._where(account_key, filters)
        row = self.session.execute(text(
            "SELECT COALESCE(SUM(CASE WHEN items.direction = 'IN' THEN items.amount_cents END), 0) AS total_in_cents, "
            "       COALESCE(SUM(CASE WHEN items.direction = 'OUT' THEN items.amount_cents END), 0) AS total_out_cents, "
            "       COALESCE(SUM(items.fee_cents), 0) AS total_fee_cents "
            f"FROM ({ITEMS_SQL}) items {where}"
        ), params).mappings().one()
        return {key: int(value) for key, value in row.items()}

    def get_item(self, account_key: str, transaction_key: str) -> dict:
        self._use_sao_paulo_time()
        row = self.session.execute(text(
            f"SELECT * FROM ({ITEMS_SQL}) items WHERE items.transaction_key = :transaction_key"
        ), {"account_key": account_key, "transaction_key": transaction_key}).mappings().first()
        return dict(row) if row is not None else None

    def entries_of(self, account_key: str, transaction_key: str) -> list:
        """Só os lançamentos desta conta: o da conta de receitas, ou o da
        outra ponta, não são da conta de quem pergunta (R8)."""
        rows = self.session.execute(text(
            "SELECT et.enumerator AS entry_type, e.amount_cents "
            "  FROM ledger_entries e "
            "  JOIN entry_types et ON et.id = e.entry_type_id "
            "  JOIN account_balances b ON b.id = e.account_balance_id "
            "  LEFT JOIN deposits d ON d.id = e.deposit_id "
            "  LEFT JOIN transfers t ON t.id = e.transfer_id "
            " WHERE b.account_key = :account_key "
            "   AND (d.deposit_key = :transaction_key OR t.transfer_key = :transaction_key) "
            " ORDER BY e.id"
        ), {"account_key": account_key, "transaction_key": transaction_key}).mappings().all()
        return [{"entry_type": row["entry_type"], "amount_cents": row["amount_cents"]} for row in rows]

    def _where(self, account_key: str, filters: dict):
        clauses = []
        params = {"account_key": account_key}
        for name, value in filters.items():
            if value is None:
                continue
            clauses.append(FILTERS[name])
            params[name] = value

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params

    def _use_sao_paulo_time(self) -> None:
        # SET LOCAL vale só até o fim desta transação: a conexão volta pro
        # pool sem levar o fuso para a próxima requisição.
        self.session.execute(text("SET LOCAL TIME ZONE 'America/Sao_Paulo'"))
