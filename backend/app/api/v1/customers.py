# backend/app/api/v1/customers.py - Enhanced Version
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from ...schemas.customer_schema import Customer, CustomerCreate, CustomerUpdate
from ...schemas.interaction_schema import InteractionCreate, InteractionResponse
from ...models.customer_model import Customer as CustomerModel
from ...models.interaction_model import Interaction
from ...core.database import get_db
from ...workflow.tasks import schedule_followup_task

router = APIRouter()

# ===== CUSTOMER CRUD =====

@router.post("/", response_model=Customer)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer"""
    logging.info(f"Creating customer: {customer.phone_number}")
    
    # Check if customer already exists
    existing = db.query(CustomerModel).filter(
        CustomerModel.phone_number == customer.phone_number
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this phone number already exists")
    
    db_customer = CustomerModel(**customer.model_dump())
    db.add(db_customer)
    
    try:
        db.commit()
        db.refresh(db_customer)
        logging.info(f"Customer created successfully: {db_customer.customer_id}")
        return db_customer
    except Exception as e:
        logging.error(f"Failed to create customer: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/{customer_id}", response_model=Customer)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a specific customer by ID"""
    db_customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return db_customer


@router.get("/", response_model=List[Customer])
def read_customers(
    skip: int = 0,
    limit: int = 100,
    customer_type: Optional[str] = Query(None, description="Filter by customer type"),
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    db: Session = Depends(get_db)
):
    """Get list of customers with optional filtering"""
    query = db.query(CustomerModel)
    
    # Filter by customer type
    if customer_type:
        query = query.filter(CustomerModel.customer_type == customer_type)
    
    # Search functionality
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (CustomerModel.first_name.ilike(search_term)) |
            (CustomerModel.last_name.ilike(search_term)) |
            (CustomerModel.phone_number.ilike(search_term)) |
            (CustomerModel.email.ilike(search_term))
        )
    
    customers = query.offset(skip).limit(limit).all()
    return customers


@router.put("/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db)
):
    """Update customer information"""
    db_customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update fields
    update_data = customer_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_customer, field, value)
    
    try:
        db.commit()
        db.refresh(db_customer)
        logging.info(f"Customer {customer_id} updated successfully")
        return db_customer
    except Exception as e:
        logging.error(f"Failed to update customer: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Delete a customer (soft delete recommended in production)"""
    db_customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        db.delete(db_customer)
        db.commit()
        logging.info(f"Customer {customer_id} deleted")
        return {"message": "Customer deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete customer: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# ===== CUSTOMER INTERACTIONS =====

@router.post("/{customer_id}/interactions", response_model=InteractionResponse)
def add_interaction(
    customer_id: int,
    interaction: InteractionCreate,
    db: Session = Depends(get_db)
):
    """Add a new interaction for a customer"""
    # Verify customer exists
    customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Create interaction
    db_interaction = Interaction(
        customer_id=customer_id,
        **interaction.model_dump()
    )
    
    db.add(db_interaction)
    
    try:
        db.commit()
        db.refresh(db_interaction)
        logging.info(f"Interaction added for customer {customer_id}")
        
        # Trigger analysis task
        from ...workflow.tasks import analyze_interaction_task
        analyze_interaction_task.delay(db_interaction.interaction_id)
        
        return db_interaction
    except Exception as e:
        logging.error(f"Failed to add interaction: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/{customer_id}/interactions", response_model=List[InteractionResponse])
def get_customer_interactions(
    customer_id: int,
    limit: int = Query(50, description="Maximum number of interactions to return"),
    db: Session = Depends(get_db)
):
    """Get all interactions for a specific customer"""
    # Verify customer exists
    customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    interactions = db.query(Interaction).filter(
        Interaction.customer_id == customer_id
    ).order_by(Interaction.interaction_timestamp.desc()).limit(limit).all()
    
    return interactions


@router.post("/{customer_id}/schedule-followup")
def schedule_customer_followup(
    customer_id: int,
    followup_type: str = Query(..., description="Type of follow-up: test_drive_confirmation, send_pricing, etc."),
    db: Session = Depends(get_db)
):
    """Schedule an automated follow-up for a customer"""
    # Verify customer exists
    customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Trigger follow-up task
    task = schedule_followup_task.delay(customer_id, followup_type)
    
    return {
        "message": f"Follow-up scheduled for customer {customer_id}",
        "followup_type": followup_type,
        "task_id": task.id
    }


@router.post("/{customer_id}/score-lead")
def manually_score_lead(
    customer_id: int,
    text_input: str = Query(..., description="Text to analyze for lead scoring"),
    db: Session = Depends(get_db)
):
    """Manually trigger lead scoring for a customer"""
    from ...workflow.tasks import score_lead_task
    
    # Verify customer exists
    customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Trigger scoring task
    task = score_lead_task.delay(customer_id, text_input)
    
    return {
        "message": f"Lead scoring queued for customer {customer_id}",
        "task_id": task.id
    }


@router.get("/{customer_id}/timeline")
def get_customer_timeline(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Get complete timeline of customer activities"""
    customer = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get all interactions
    interactions = db.query(Interaction).filter(
        Interaction.customer_id == customer_id
    ).order_by(Interaction.interaction_timestamp.desc()).all()
    
    # Get all documents
    from ...models.document_model import Document
    documents = db.query(Document).filter(
        Document.customer_id == customer_id
    ).order_by(Document.created_at.desc()).all()
    
    # Combine into timeline
    timeline = []
    
    for interaction in interactions:
        timeline.append({
            "type": "interaction",
            "timestamp": interaction.interaction_timestamp.isoformat(),
            "channel": interaction.channel,
            "summary": interaction.summary or "No summary available",
            "outcome": interaction.outcome,
            "sentiment": interaction.sentiment
        })
    
    for doc in documents:
        timeline.append({
            "type": "document",
            "timestamp": doc.created_at.isoformat(),
            "document_type": doc.document_type,
            "file_path": doc.file_path
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "customer_id": customer_id,
        "customer_name": f"{customer.first_name} {customer.last_name or ''}".strip(),
        "customer_type": customer.customer_type,
        "timeline": timeline
    }


@router.get("/stats/by-type")
def get_customers_by_type(db: Session = Depends(get_db)):
    """Get customer count grouped by type"""
    from sqlalchemy import func
    
    stats = db.query(
        CustomerModel.customer_type,
        func.count(CustomerModel.customer_id).label('count')
    ).group_by(CustomerModel.customer_type).all()
    
    return {
        customer_type: count
        for customer_type, count in stats
    }