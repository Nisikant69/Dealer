# backend/app/main.py - Complete Version
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

# Import all routers
from .api.v1 import customers, documents, lead_intelligence, analytics
from .api.v1 import voice as voice_agent_router

# Import database setup
from .core.database import engine, Base 
from .models import customer_model, vehicle_model, document_model, interaction_model

# Import Celery for testing
from .workflow.tasks import test_celery_task
from celery.result import AsyncResult
from .core.celery_app import celery_app

# Create database tables
Base.metadata.create_all(bind=engine)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI App
app = FastAPI(
    title="Dealership AI Backend API",
    description="Privacy-First Agentic AI System for Premium Automotive Dealerships",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "*"  # For development only - restrict in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
logger.info("Registering API routers...")

# Core customer management
app.include_router(
    customers.router,
    prefix="/api/v1/customers",
    tags=["👥 Customers"]
)

# Document generation
app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["📄 Documents"]
)

# Lead intelligence and scoring
app.include_router(
    lead_intelligence.router,
    prefix="/api/v1/leads",
    tags=["🎯 Lead Intelligence"]
)

# Analytics and reporting
app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["📊 Analytics & Insights"]
)

# Voice agent webhooks
app.include_router(
    voice_agent_router.router,
    prefix="/api/v1/voice",
    tags=["📞 Voice Agent"]
)

logger.info("✅ All routers registered successfully")

# Root Endpoint
@app.get("/", tags=["System"])
def read_root():
    """Welcome endpoint with API information"""
    return {
        "message": "🚀 Dealership AI Backend API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "health_check": "/health",
        "features": [
            "Voice Agent Integration (Vapi)",
            "Intelligent Lead Scoring",
            "Automated Document Generation",
            "Multi-Channel Communication",
            "Real-time Analytics",
            "Privacy-First Architecture"
        ]
    }

# Health Check Endpoint
@app.get("/health", tags=["System"])
def health_check():
    """Comprehensive health check for all system components"""
    try:
        # Test database connection
        from .core.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"
    
    # Test Redis connection
    try:
        import redis
        from .core.config import settings
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = f"error: {str(e)}"
    
    # Test Celery
    try:
        celery_app.control.inspect().active()
        celery_status = "active"
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        celery_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "Dealership AI Backend",
        "timestamp": time.time(),
        "components": {
            "database": db_status,
            "redis": redis_status,
            "celery": celery_status,
            "voice_agent": "configured",
            "email_service": "configured"
        },
        "agents": {
            "voice_agent": "active",
            "lead_intelligence": "active",
            "document_generator": "active",
            "communication_agent": "active"
        }
    }

# Celery Test Endpoints
@app.post("/test-task", tags=["System"])
def run_test_task():
    """Trigger a test Celery task to verify worker connectivity"""
    task = test_celery_task.delay("Hello from API")
    return {
        "message": "Test task has been queued",
        "task_id": task.id,
        "check_status": f"/task-status/{task.id}"
    }

@app.get("/task-status/{task_id}", tags=["System"])
def get_task_status(task_id: str):
    """Check the status of a Celery task"""
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None
    }
    
    if task_result.ready():
        try:
            response["result"] = task_result.result
        except Exception as e:
            response["result"] = f"Error: {str(e)}"
    
    return response

# System Information Endpoint
@app.get("/system-info", tags=["System"])
def get_system_info():
    """Get detailed system configuration and statistics"""
    from .core.config import settings
    from .core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Count records
        customer_count = db.query(customer_model.Customer).count()
        interaction_count = db.query(interaction_model.Interaction).count()
        document_count = db.query(document_model.Document).count()
        
        return {
            "system": {
                "name": "Dealership AI Backend",
                "version": "1.0.0",
                "environment": "production"
            },
            "configuration": {
                "smtp_configured": bool(settings.SMTP_HOST),
                "vapi_configured": bool(settings.VAPI_API_KEY),
                "redis_configured": bool(settings.REDIS_URL)
            },
            "database_stats": {
                "total_customers": customer_count,
                "total_interactions": interaction_count,
                "total_documents": document_count
            },
            "features": {
                "voice_calling": "enabled",
                "lead_scoring": "enabled",
                "document_generation": "enabled",
                "email_automation": "enabled",
                "analytics": "enabled"
            }
        }
    finally:
        db.close()

# Startup Event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("\n" + "="*80)
    print("🚀 DEALERSHIP AI BACKEND STARTING...")
    print("="*80)
    print("\n📋 API Endpoints:")
    
    # Group routes by tags
    routes_by_tag = {}
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "tags"):
            tags = route.tags if route.tags else ["Untagged"]
            for tag in tags:
                if tag not in routes_by_tag:
                    routes_by_tag[tag] = []
                methods = ", ".join(route.methods)
                routes_by_tag[tag].append(f"   {methods:8} {route.path}")
    
    for tag, routes in sorted(routes_by_tag.items()):
        print(f"\n{tag}:")
        for route in routes:
            print(route)
    
    print("\n" + "="*80)
    print("✅ BACKEND IS READY!")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Alternative Docs: http://localhost:8000/redoc")
    print("💚 Health Check: http://localhost:8000/health")
    print("="*80 + "\n")

# Shutdown Event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("\n" + "="*80)
    print("👋 DEALERSHIP AI BACKEND SHUTTING DOWN...")
    print("="*80 + "\n")

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request details
    logger.info(
        f"{request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Time: {process_time:.3f}s"
    )
    
    return response

# Error Handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return {
        "error": "Not Found",
        "message": f"The endpoint {request.url.path} does not exist",
        "documentation": "/docs"
    }

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please contact support.",
        "request_path": request.url.path
    }