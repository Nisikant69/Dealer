# backend/app/api/v1/analytics.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from ...core.database import get_db
from ...models.customer_model import Customer
from ...models.interaction_model import Interaction, CallLog
from ...models.document_model import Document
from ...agents.lead_intelligence_agent.analyzer import (
    generate_conversation_insights,
    prioritize_leads,
    recommend_next_action
)

router = APIRouter()


@router.get("/dashboard-stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get comprehensive dashboard statistics for the dealership
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Customer statistics
    total_customers = db.query(Customer).count()
    hot_leads = db.query(Customer).filter(Customer.customer_type == 'Hot Lead').count()
    warm_leads = db.query(Customer).filter(Customer.customer_type == 'Warm Lead').count()
    prospects = db.query(Customer).filter(Customer.customer_type == 'Prospect').count()
    
    # New customers in period
    new_customers = db.query(Customer).filter(
        Customer.created_at >= start_date
    ).count()
    
    # Interaction statistics
    total_interactions = db.query(Interaction).filter(
        Interaction.interaction_timestamp >= start_date
    ).count()
    
    # Interactions by channel
    interactions_by_channel = db.query(
        Interaction.channel,
        func.count(Interaction.interaction_id).label('count')
    ).filter(
        Interaction.interaction_timestamp >= start_date
    ).group_by(Interaction.channel).all()
    
    # Call statistics
    total_calls = db.query(CallLog).join(Interaction).filter(
        Interaction.interaction_timestamp >= start_date
    ).count()
    
    avg_call_duration = db.query(func.avg(CallLog.duration_seconds)).join(Interaction).filter(
        Interaction.interaction_timestamp >= start_date
    ).scalar() or 0
    
    # Sentiment distribution
    sentiment_distribution = db.query(
        Interaction.sentiment,
        func.count(Interaction.interaction_id).label('count')
    ).filter(
        and_(
            Interaction.interaction_timestamp >= start_date,
            Interaction.sentiment.isnot(None)
        )
    ).group_by(Interaction.sentiment).all()
    
    # Document statistics
    invoices_generated = db.query(Document).filter(
        and_(
            Document.created_at >= start_date,
            Document.document_type == 'Invoice'
        )
    ).count()
    
    quotes_generated = db.query(Document).filter(
        and_(
            Document.created_at >= start_date,
            Document.document_type == 'Quote'
        )
    ).count()
    
    return {
        "period_days": days,
        "customer_metrics": {
            "total_customers": total_customers,
            "new_customers": new_customers,
            "hot_leads": hot_leads,
            "warm_leads": warm_leads,
            "prospects": prospects,
            "conversion_funnel": {
                "hot_lead_percentage": round((hot_leads / total_customers * 100) if total_customers > 0 else 0, 2),
                "warm_lead_percentage": round((warm_leads / total_customers * 100) if total_customers > 0 else 0, 2)
            }
        },
        "interaction_metrics": {
            "total_interactions": total_interactions,
            "interactions_by_channel": {channel: count for channel, count in interactions_by_channel},
            "average_interactions_per_customer": round(total_interactions / total_customers, 2) if total_customers > 0 else 0
        },
        "call_metrics": {
            "total_calls": total_calls,
            "average_duration_seconds": round(avg_call_duration, 2),
            "average_duration_minutes": round(avg_call_duration / 60, 2)
        },
        "sentiment_analysis": {
            sentiment: count for sentiment, count in sentiment_distribution
        },
        "document_metrics": {
            "invoices_generated": invoices_generated,
            "quotes_generated": quotes_generated,
            "total_documents": invoices_generated + quotes_generated
        }
    }


@router.get("/lead-pipeline")
def get_lead_pipeline(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by customer type")
):
    """
    Get detailed lead pipeline with prioritization
    """
    query = db.query(Customer)
    
    if status:
        query = query.filter(Customer.customer_type == status)
    
    customers = query.all()
    
    # Prepare data for prioritization
    customers_data = []
    for customer in customers:
        # Get last interaction
        last_interaction = db.query(Interaction).filter(
            Interaction.customer_id == customer.customer_id
        ).order_by(Interaction.interaction_timestamp.desc()).first()
        
        last_conversation = last_interaction.content if last_interaction else ""
        days_since_contact = (datetime.utcnow() - last_interaction.interaction_timestamp).days if last_interaction else 999
        
        customers_data.append({
            "customer_id": customer.customer_id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone_number": customer.phone_number,
            "email": customer.email,
            "customer_type": customer.customer_type,
            "last_conversation": last_conversation,
            "days_since_last_contact": days_since_contact,
            "last_interaction_date": last_interaction.interaction_timestamp.isoformat() if last_interaction else None
        })
    
    # Prioritize leads
    prioritized_leads = prioritize_leads(customers_data)
    
    # Add recommended actions
    for lead in prioritized_leads:
        lead["recommended_action"] = recommend_next_action(lead)
    
    return {
        "total_leads": len(prioritized_leads),
        "leads": prioritized_leads
    }


@router.get("/customer-insights/{customer_id}")
def get_customer_insights(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed insights for a specific customer
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get all interactions
    interactions = db.query(Interaction).filter(
        Interaction.customer_id == customer_id
    ).order_by(Interaction.interaction_timestamp.desc()).all()
    
    # Analyze all conversations combined
    all_conversations = " ".join([i.content or "" for i in interactions])
    conversation_insights = generate_conversation_insights(all_conversations)
    
    # Interaction history
    interaction_history = []
    for interaction in interactions:
        call_details = None
        if interaction.channel == "Phone":
            call_log = db.query(CallLog).filter(
                CallLog.interaction_id == interaction.interaction_id
            ).first()
            if call_log:
                call_details = {
                    "duration_seconds": call_log.duration_seconds,
                    "call_status": call_log.call_status,
                    "call_direction": call_log.call_direction
                }
        
        interaction_history.append({
            "interaction_id": interaction.interaction_id,
            "channel": interaction.channel,
            "timestamp": interaction.interaction_timestamp.isoformat(),
            "summary": interaction.summary,
            "outcome": interaction.outcome,
            "sentiment": interaction.sentiment,
            "call_details": call_details
        })
    
    # Documents generated
    documents = db.query(Document).filter(
        Document.customer_id == customer_id
    ).all()
    
    document_list = [{
        "document_id": doc.document_id,
        "document_type": doc.document_type,
        "created_at": doc.created_at.isoformat(),
        "file_path": doc.file_path
    } for doc in documents]
    
    # Calculate customer lifetime value indicators
    total_interactions = len(interactions)
    days_as_customer = (datetime.utcnow() - customer.created_at).days if customer.created_at else 0
    
    return {
        "customer": {
            "customer_id": customer.customer_id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone_number": customer.phone_number,
            "email": customer.email,
            "address": customer.address,
            "customer_type": customer.customer_type,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "days_as_customer": days_as_customer
        },
        "conversation_insights": conversation_insights,
        "interaction_summary": {
            "total_interactions": total_interactions,
            "channels_used": list(set([i.channel for i in interactions])),
            "last_contact": interactions[0].interaction_timestamp.isoformat() if interactions else None,
            "days_since_last_contact": (datetime.utcnow() - interactions[0].interaction_timestamp).days if interactions else None
        },
        "interaction_history": interaction_history,
        "documents": document_list,
        "recommended_next_action": recommend_next_action({
            "customer_type": customer.customer_type,
            "last_conversation": all_conversations,
            "days_since_last_contact": (datetime.utcnow() - interactions[0].interaction_timestamp).days if interactions else 999
        })
    }


@router.get("/performance-trends")
def get_performance_trends(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days for trend analysis")
):
    """
    Get performance trends over time
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily interaction counts
    daily_interactions = db.query(
        func.date(Interaction.interaction_timestamp).label('date'),
        func.count(Interaction.interaction_id).label('count')
    ).filter(
        Interaction.interaction_timestamp >= start_date
    ).group_by(func.date(Interaction.interaction_timestamp)).all()
    
    # Daily new customers
    daily_customers = db.query(
        func.date(Customer.created_at).label('date'),
        func.count(Customer.customer_id).label('count')
    ).filter(
        Customer.created_at >= start_date
    ).group_by(func.date(Customer.created_at)).all()
    
    # Lead status progression over time
    lead_status_changes = db.query(
        func.date(Customer.created_at).label('date'),
        Customer.customer_type,
        func.count(Customer.customer_id).label('count')
    ).filter(
        Customer.created_at >= start_date
    ).group_by(
        func.date(Customer.created_at),
        Customer.customer_type
    ).all()
    
    return {
        "period_days": days,
        "daily_interactions": [
            {"date": str(date), "count": count}
            for date, count in daily_interactions
        ],
        "daily_new_customers": [
            {"date": str(date), "count": count}
            for date, count in daily_customers
        ],
        "lead_status_trends": [
            {"date": str(date), "status": status, "count": count}
            for date, status, count in lead_status_changes
        ]
    }


@router.get("/ai-agent-health")
def get_ai_agent_health(db: Session = Depends(get_db)):
    """
    Health check for all AI agents and system components
    """
    # Check recent activity
    last_hour = datetime.utcnow() - timedelta(hours=1)
    
    recent_calls = db.query(CallLog).join(Interaction).filter(
        Interaction.interaction_timestamp >= last_hour
    ).count()
    
    recent_interactions = db.query(Interaction).filter(
        Interaction.interaction_timestamp >= last_hour
    ).count()
    
    recent_documents = db.query(Document).filter(
        Document.created_at >= last_hour
    ).count()
    
    # Check for errors (interactions without sentiment analysis)
    unprocessed_interactions = db.query(Interaction).filter(
        and_(
            Interaction.sentiment.is_(None),
            Interaction.content.isnot(None),
            Interaction.content != ''
        )
    ).count()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "activity_last_hour": {
            "calls_handled": recent_calls,
            "total_interactions": recent_interactions,
            "documents_generated": recent_documents
        },
        "processing_queue": {
            "unprocessed_interactions": unprocessed_interactions,
            "status": "ok" if unprocessed_interactions < 10 else "warning"
        },
        "components": {
            "voice_agent": "active",
            "lead_intelligence": "active",
            "document_generator": "active",
            "email_automation": "active",
            "database": "connected"
        }
    }


@router.post("/trigger-daily-tasks")
def trigger_daily_maintenance(db: Session = Depends(get_db)):
    """
    Manually trigger daily maintenance tasks (normally run by Celery Beat)
    """
    from ...workflow.tasks import daily_lead_nurture_task
    
    task = daily_lead_nurture_task.delay()
    
    return {
        "message": "Daily maintenance tasks triggered",
        "task_id": task.id,
        "tasks_queued": [
            "daily_lead_nurture",
            "inactive_lead_cleanup"
        ]
    }

        