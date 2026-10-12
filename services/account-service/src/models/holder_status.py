from sqlalchemy import Column, Integer, String

from models.base import Base


class HolderStatus(Base):
    __tablename__ = "holder_status"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
