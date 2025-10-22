from pydantic import BaseModel
from typing import Optional

# Schema for creating a customer (input)
class CustomerCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    address: Optional[str] = None

# Schema for reading a customer (output)
class Customer(CustomerCreate):
    customer_id: int
    customer_type: str

    class Config:
        from_attributes = True # Pydantic v2
        # orm_mode = True for Pydantic v1