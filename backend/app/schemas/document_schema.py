from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    document_type: str = Field(..., description="Document type: Invoice, Quote, Proforma")

class DocumentCreate(DocumentBase):
    """Schema for document generation request"""
    customer_id: int
    vehicle_id: Optional[int] = None

class DocumentResponse(DocumentBase):
    """Schema for reading document (output)"""
    document_id: int
    customer_id: int
    file_path: str
    created_at: datetime

    class Config:
        from_attributes = True