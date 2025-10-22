from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...workflow.tasks import score_lead_task # Import the Celery task

router = APIRouter()

class LeadScoreRequest(BaseModel):
    customer_id: int
    text_input: str # The text to analyze (e.g., from a form or transcript)

@router.post("/score-lead", status_code=202) # Use 202 Accepted for async tasks
def trigger_lead_scoring(request: LeadScoreRequest):
    """
    Triggers the asynchronous scoring of a lead based on text input.
    """
    if not request.text_input.strip():
        raise HTTPException(status_code=400, detail="text_input cannot be empty")

    # Dispatch the task to Celery. The API's job is done.
    task = score_lead_task.delay(request.customer_id, request.text_input)

    return {"message": "Lead scoring task has been queued.", "task_id": task.id}
