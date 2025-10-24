from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class CustomerBase(BaseModel):
    phone_number: str = Field(..., description="Customer's phone number")
    first_name: Optional[str] = "Unknown"
    last_name: Optional[str] = "Caller"
    email: Optional[EmailStr] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    """Schema for creating a new customer"""
    pass

class CustomerUpdate(BaseModel):
    """Schema for updating customer information"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    customer_type: Optional[str] = None

class Customer(CustomerBase):
    """Schema for reading a customer (output)"""
    customer_id: int
    customer_type: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
