from datetime import date
from uuid import uuid4

from database import Context
from models import Customer


class CustomerRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, customer_data: dict) -> Customer:
        customer = Customer()

        customer.customer_key = str(uuid4())
        customer.document_number = customer_data["document_number"]
        customer.name = customer_data["name"]
        customer.mother_name = customer_data["mother_name"]
        customer.birthdate = date.fromisoformat(customer_data["birthdate"])
        customer.birth_city = customer_data["birth_city"]
        customer.residence_city = customer_data["residence_city"]
        customer.income_cents = customer_data["income_cents"]
        customer.email = customer_data["email"]
        customer.phone = customer_data["phone"]

        self.session.add(customer)
        return customer

    def get_by_document_number(self, document_number: str) -> Customer:
        return self.session.query(Customer).filter(Customer.document_number == document_number).first()
