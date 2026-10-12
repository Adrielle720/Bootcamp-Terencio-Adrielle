from models import Customer, Document


def _iso(moment):
    return moment.isoformat() if moment is not None else None


def pendency_to_dict(pendency, reason: str) -> dict:
    return {
        "reason": reason,
        "description": pendency.description,
        "created_at": _iso(pendency.created_at),
        "resolved_at": _iso(pendency.resolved_at),
    }


def customer_to_dict(customer: Customer, status: str, open_pendencies: list) -> dict:
    return {
        "customer_key": customer.customer_key,
        "status": status,
        "document_number": customer.document_number,
        "name": customer.name,
        "mother_name": customer.mother_name,
        "birth_date": customer.birth_date.isoformat(),
        "birth_city": customer.birth_city,
        "residence_city": customer.residence_city,
        "income_cents": customer.income_cents,
        "email": customer.email,
        "phone": customer.phone,
        "created_at": _iso(customer.created_at),
        "pendencies": [
            {**pendency_to_dict(pendency, reason), "document_key": document.document_key}
            for pendency, reason, document in open_pendencies
        ],
    }


def customer_to_internal_dict(customer: Customer, status: str) -> dict:
    """O que os outros serviços precisam saber: status, contatos atuais e os dados que nunca mudam."""
    return {
        "customer_key": customer.customer_key,
        "status": status,
        "email": customer.email,
        "phone": customer.phone,
        "name": customer.name,
        "mother_name": customer.mother_name,
        "document_number": customer.document_number,
        "birth_date": customer.birth_date.isoformat(),
    }


def document_to_dict(document: Document, document_type: str, status: str, pendencies: list) -> dict:
    return {
        "document_key": document.document_key,
        "document_type": document_type,
        "status": status,
        "document_number": document.document_number,
        "expiration_date": _iso(document.expiration_date),
        "created_at": _iso(document.created_at),
        "pendencies": [pendency_to_dict(pendency, reason) for pendency, reason in pendencies],
    }


def document_to_internal_dict(document: Document, document_type: str, status: str, owner_customer_key: str) -> dict:
    return {
        "document_key": document.document_key,
        "document_type": document_type,
        "status": status,
        "customer_key": owner_customer_key,
    }
