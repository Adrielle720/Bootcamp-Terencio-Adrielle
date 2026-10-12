def item_to_dict(row: dict) -> dict:
    """Uma operação do extrato. Depósito não tem outra ponta; transferência tem."""
    counterparty = None
    if row["counterparty_account_number"] is not None:
        counterparty = {
            "account_number": row["counterparty_account_number"],
            "name": row["counterparty_name"],
        }

    return {
        "transaction_key": row["transaction_key"],
        "type": row["type"],
        "direction": row["direction"],
        "amount_cents": row["amount_cents"],
        "fee_cents": row["fee_cents"],
        "total_cents": row["amount_cents"] + row["fee_cents"],
        "created_at": row["created_at"].isoformat(),
        "made_by": {"name": row["made_by_name"]},
        "counterparty": counterparty,
    }
