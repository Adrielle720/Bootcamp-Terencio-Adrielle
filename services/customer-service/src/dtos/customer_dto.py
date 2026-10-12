from models import Customer


def customer_to_dict(customer: Customer) -> dict:
    return {
        "customer_key": customer.customer_key,
        "document_number": customer.document_number,
        "name": customer.name,
        "mother_name": customer.mother_name,
        "birth_date": customer.birthdate.isoformat(),
        "birth_city": customer.birth_city,
        "residence_city": customer.residence_city,
        "income_cents": customer.income_cents,
        "email": customer.email,
        "phone": customer.phone,
        "created_at": customer.created_at.isoformat(),
    }
