from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

from .api.v1 import customers, documents, lead_intelligence
from .agents.voice_agent import handler as voice_handler 
from .api.v1 import voice as voice_agent_router
from .core.database import engine, Base 
from .models import customer_model, vehicle_model, document_model

from .workflow.tasks import test_celery_task
from celery.result import AsyncResult
from .core.celery_app import celery_app

# Create database tables

# backend/app/main.py


Base.metadata.create_all(bind=engine)

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Create FastAPI App ---
app = FastAPI(
    title="Dealership Backend API",
    description="API for managing customers, documents, and lead intelligence.",
    version="0.1.0"
)

# --- Configure CORS ---
# Adjust origins as needed for your frontend/testing
origins = [
    "http://localhost",
    "http://localhost:3000", # Example for React frontend
    # Add other origins if necessary
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include API Routers ---
logger.info("Including API routers...")

# Include your existing routers
app.include_router(customers.router, prefix="/api/v1/customers", tags=["Customers"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(lead_intelligence.router, prefix="/api/v1/leads", tags=["Lead Intelligence"])

# <<< ADD THIS SECTION TO INCLUDE THE VOICE AGENT ROUTER >>>
app.include_router(
    voice_agent_router.router, # The router instance imported from voice.py
    prefix="/api/v1/voice",    # The base path for routes in voice.py
    tags=["Voice Agent"]       # Optional tag for API docs
)
# <<< END ADD SECTION >>>

logger.info("Routers included successfully.")

# --- Root Endpoint ---
@app.get("/")
def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to the Dealership Backend API"}

# --- Add other startup/shutdown events if needed ---
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Application startup...")

# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Application shutdown.")

# Health check endpoint
@app.get("/health")
def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "service": "Dealership AI Backend",
        "components": {
            "database": "connected",
            "voice_agent": "active",
            "celery": "active"
        }
    }

# Celery test endpoints
@app.post("/test-task")
def run_test_task():
    """Trigger a test Celery task"""
    task = test_celery_task.delay("Hello Workflow")
    return {
        "message": "Test task has been queued",
        "task_id": task.id,
        "check_status": f"/task-status/{task.id}"
    }

@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    """Check the status of a Celery task"""
    task_result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("\n" + "="*70)
    print("🚀 Dealership AI Backend Starting...")
    print("="*70)
    print("\n📋 Registered Routes:")
    for route in app.routes:
        if hasattr(route, "methods"):
            methods = ", ".join(route.methods)
            print(f"   {methods:8} {route.path}")
    print("\n" + "="*70)
    print("✅ Backend is ready!")
    print("="*70 + "\n")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("\n" + "="*70)
    print("👋 Dealership AI Backend Shutting Down...")
    print("="*70 + "\n")