from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InteractionBase(BaseModel):
    channel: str = Field(..., description="Communication channel: Phone, Email, WhatsApp, In-Person")
    content: Optional[str] = Field(None, description="Full content/transcript of interaction")
    summary: Optional[str] = Field(None, description="Brief summary of interaction")
    outcome: Optional[str] = Field(None, description="Outcome: Test drive scheduled, Quote sent, etc.")

class InteractionCreate(InteractionBase):
    """Schema for creating a new interaction"""
    pass

class InteractionResponse(InteractionBase):
    """Schema for reading interaction (output)"""
    interaction_id: int
    customer_id: int
    sentiment: Optional[str] = None
    lead_score_impact: Optional[int] = None
    interaction_timestamp: datetime

    class Config:
        from_attributes = True