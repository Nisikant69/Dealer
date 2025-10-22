from fastapi import APIRouter
from pydantic import BaseModel
from ...workflow.tasks import generate_invoice_task

router = APIRouter()

class InvoiceRequest(BaseModel):
    customer_id: int
    vehicle_id: int

@router.post("/generate-invoice")
def trigger_invoice_generation(request: InvoiceRequest):
    """
    Triggers the asynchronous generation of an invoice.
    """
    task = generate_invoice_task.delay(request.customer_id, request.vehicle_id)
    return {"message": "Invoice generation has been queued.", "task_id": task.id}