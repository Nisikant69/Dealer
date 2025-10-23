from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class CustomerBase(BaseModel):
    phone_number: str = Field(..., description="Customer's phone number")
    # Make other fields optional and provide defaults
    first_name: Optional[str] = "11"
    last_name: Optional[str] = "Caller"
    email: Optional[EmailStr] = None 
    # Add any other fields from your Customer model here, making them Optional

class CustomerCreate(CustomerBase):
    # Inherits fields from CustomerBase. 
    # No need to redefine if they are the same for creation.
    pass
# Schema for reading a customer (output)
class Customer(CustomerCreate):
    customer_id: int
    customer_type: str

    class Config:
        from_attributes = True # Pydantic v2
        # orm_mode = True for Pydantic v1