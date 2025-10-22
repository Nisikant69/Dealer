from sqlalchemy import Column, Integer, String, Text
from ..core.database import Base

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    address = Column(Text)
    customer_type = Column(String, default='Prospect')