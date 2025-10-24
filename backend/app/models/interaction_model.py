from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base

class Interaction(Base):
    """
    Tracks all customer interactions across channels (phone, email, WhatsApp, in-person)
    """
    __tablename__ = "interactions"

    interaction_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True)
    channel = Column(String(50), nullable=False)  # Phone, Email, WhatsApp, In-Person
    content = Column(Text)  # Transcript, email body, or meeting notes
    summary = Column(Text)  # AI-generated summary
    outcome = Column(String(255))  # Test drive scheduled, Quote sent, etc.
    sentiment = Column(String(50))  # Positive, Neutral, Negative
    lead_score_impact = Column(Integer)  # How this interaction affected lead score
    interaction_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to Customer
    customer = relationship("Customer", backref="interactions")

class CallLog(Base):
    """
    Specific details for voice interactions
    """
    __tablename__ = "call_logs"

    call_log_id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.interaction_id", ondelete="CASCADE"))
    call_sid = Column(String(255))  # Vapi call ID
    duration_seconds = Column(Integer)
    recording_path = Column(String(255))  # Local path to recording
    call_status = Column(String(50))  # Completed, No Answer, Failed
    call_direction = Column(String(20))  # Inbound, Outbound
    
    # Relationship to Interaction
    interaction = relationship("Interaction", backref="call_details")