from datetime import datetime

from models import Account, AccountHolder, Customer


def _iso(moment: datetime):
    return moment.isoformat() if moment is not None else None


def holder_to_dict(holder: AccountHolder, customer: Customer, status: str) -> dict:
    """Um titular como os outros titulares o veem.

    Nenhum id interno sai: só a account_holder_key. O contato do convite
    aparece enquanto a pessoa ainda não é cliente, para o grupo saber quem
    foi chamado.
    """
    return {
        "account_holder_key": holder.holder_key,
        "name": customer.name if customer is not None else None,
        "role": holder.role,
        "status": status,
        "invited_email": holder.invited_email if customer is None else None,
        "invited_phone": holder.invited_phone if customer is None else None,
        "monthly_limit_cents": holder.monthly_limit_cents,
        "invited_at": _iso(holder.invited_at),
        "joined_at": _iso(holder.joined_at),
        "left_at": _iso(holder.left_at),
    }


def account_to_dict(account: Account, status: str, balance_cents: int, holders: list) -> dict:
    return {
        "account_key": account.account_key,
        "account_number": account.account_number,
        "name": account.name,
        "status": status,
        "balance_cents": balance_cents,
        "transfer_limit_cents": account.transfer_limit_cents,
        "created_at": _iso(account.created_at),
        "holders": holders,
    }


def invitation_to_dict(holder: AccountHolder, account: Account) -> dict:
    return {
        "account_holder_key": holder.holder_key,
        "account_key": account.account_key,
        "account_name": account.name,
        "invited_at": _iso(holder.invited_at),
    }
