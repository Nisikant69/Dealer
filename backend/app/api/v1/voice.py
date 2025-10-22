from fastapi import APIRouter, Request

# Import the handler function
from ...agents.voice_agent.handler import handle_vapi_webhook

router = APIRouter()

@router.post("/webhook")
async def vapi_webhook_endpoint(request: Request):
    """
    This single endpoint receives all webhook events from Vapi
    and passes them to the handler for processing.
    """
    return await handle_vapi_webhook(request)
