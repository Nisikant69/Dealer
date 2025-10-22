from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from ..core.database import Base

class Document(Base):
    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    document_type = Column(String, nullable=False) # 'Invoice', 'Quote'
    file_path = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())