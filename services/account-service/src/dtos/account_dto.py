from datetime import datetime

from models import Account, AccountHolder


def _iso(moment: datetime):
    return moment.isoformat() if moment is not None else None


def holder_to_dict(holder: AccountHolder, role: str, status: str) -> dict:
    """Um titular como os outros titulares o veem.

    Nenhum id interno sai: só a account_holder_key. O contato do convite
    aparece enquanto a pessoa ainda não aceitou, para o grupo saber quem
    foi chamado. O nome é a cópia feita no aceite.
    """
    accepted = holder.name is not None
    return {
        "account_holder_key": holder.account_holder_key,
        "name": holder.name,
        "role": role,
        "status": status,
        "invited_email": None if accepted else holder.invited_email,
        "invited_phone": None if accepted else holder.invited_phone,
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
        "account_holder_key": holder.account_holder_key,
        "account_key": account.account_key,
        "account_name": account.name,
        "invited_at": _iso(holder.invited_at),
    }
