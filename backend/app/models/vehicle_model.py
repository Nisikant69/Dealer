from sqlalchemy import Column, Integer, String, Numeric, JSON
from ..core.database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    brand = Column(String)
    base_price = Column(Numeric(15, 2), nullable=False)
    configuration_details = Column(JSON)