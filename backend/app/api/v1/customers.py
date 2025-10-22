from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging
# Import the Pydantic schemas correctly
from ...schemas.customer_schema import Customer, CustomerCreate
from ...models.customer_model import Customer as CustomerModel
from ...core.database import get_db

router = APIRouter()

# CREATE
@router.post("/", response_model=Customer)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    # Use the imported CustomerModel here
    logging.warning(f"Attempting to create customer: {customer.model_dump()}") # Log input
    db_customer = CustomerModel(**customer.model_dump())
    db.add(db_customer)
    try:
        logging.warning("Attempting to commit...")
        db.commit()
        logging.warning(f"Commit successful for ID (pre-refresh): {db_customer.customer_id}")
        db.refresh(db_customer)
        logging.warning(f"Refresh successful for ID: {db_customer.customer_id}, Email: {db_customer.email}")
        return db_customer
    except Exception as e:
        logging.error(f"Commit failed! Rolling back. Error: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")

# READ ONE
@router.get("/{customer_id}", response_model=Customer)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    # Use the imported CustomerModel here
    db_customer = db.query(CustomerModel).filter(CustomerModel.customer_id == customer_id).first()
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return db_customer

# READ ALL
@router.get("/", response_model=List[Customer])
def read_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Use the imported CustomerModel here
    customers = db.query(CustomerModel).offset(skip).limit(limit).all()
    return customers