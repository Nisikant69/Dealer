from fastapi import FastAPI
from .api.v1 import customers, documents, lead_intelligence, voice
from .core.database import engine, Base 
from .models import customer_model, vehicle_model, document_model

# --- NEW IMPORTS ---
from .workflow.tasks import test_celery_task
from celery.result import AsyncResult
from .core.celery_app import celery_app
# --- END NEW IMPORTS ---

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dealership AI Backend")

# Include the customer API routes
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(lead_intelligence.router, prefix="/api/v1/intelligence", tags=["intelligence"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])

@app.get("/")
def read_root():
    return {"status": "Dealership AI Backend is running"}

# --- NEW TEST ENDPOINT ---
@app.post("/test-task")
def run_test_task():
    """
    Triggers a test Celery task.
    """
    # This sends the task to the Celery worker via Redis
    task = test_celery_task.delay("Hello Workflow")
    return {"message": "Test task has been sent!", "task_id": task.id}

@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    """
    Checks the status of a Celery task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result
    }