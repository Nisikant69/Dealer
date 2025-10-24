from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal

class VehicleBase(BaseModel):
    model_name: str = Field(..., description="Vehicle model name")
    brand: str = Field(..., description="Vehicle brand")
    base_price: Decimal = Field(..., description="Base price in INR")
    configuration_details: Optional[Dict[str, Any]] = Field(None, description="Custom configuration JSON")

class VehicleCreate(VehicleBase):
    """Schema for adding a new vehicle"""
    pass

class Vehicle(VehicleBase):
    """Schema for reading vehicle (output)"""
    vehicle_id: int

    class Config:
        from_attributes = True