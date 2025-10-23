# backend/app/agents/voice_agent/voice.py
import datetime # Added for health check
from fastapi import APIRouter, Request, Response # Added Response
import redis # Added for health check

# Import ONLY the server webhook handler function
from ...agents.voice_agent.handler import vapi_server_webhook # Adjusted relative import path
from ...core.config import settings # Added for health check (optional, depends on redis_client scope)

# --- Define Router ---
router = APIRouter()

# --- Reconnect Redis Client for Health Check (if needed, better practice is dependency injection) ---
# NOTE: This duplicates connection logic. Ideally, pass redis_client via dependency injection.
try:
    redis_client_health = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client_health.ping()
    redis_available = True
except Exception:
    redis_available = False
    redis_client_health = None # Ensure it's defined
# --- End Redis Connection for Health Check ---

@router.post("/webhook")
async def vapi_webhook_endpoint(request: Request):
    """
    This single endpoint receives all SERVER webhook events from Vapi
    and passes them to the handler for processing.
    """
    return await vapi_server_webhook(request)

# --- Add Health Check Route Here ---
@router.get("/webhook/health")
def voice_health_check():
    """Health check endpoint for the voice agent webhook service."""
    redis_status = "disconnected"
    if redis_available and redis_client_health: # Check availability
        try:
            # Re-ping just to be sure, though initial check might suffice
            redis_client_health.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error - {e}"
    elif redis_client_health: # Connected initially but ping failed
         redis_status = "error - ping failed"

    status = {
        "status": "healthy",
        "service": "Voice Agent Webhooks",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "redis_connection": redis_status
            # Removed Ollama check as it's not used by this service anymore
        }
    }
    # Consider adding basic check for VAPI_API_KEY if needed
    # status["dependencies"]["vapi_key_set"] = bool(settings.VAPI_API_KEY)
    print(f"[HEALTH CHECK] Status: {status}")
    return status
# --- End Health Check Route ---