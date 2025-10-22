import json
import httpx
import redis
import datetime
from fastapi import Request, Response, APIRouter
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.database import SessionLocal
from ...models.customer_model import Customer
from ...workflow.tasks import score_lead_task

router = APIRouter()

# --- REDIS & HTTPX CLIENTS (Keep these as they were) ---
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("[VOICE AGENT] Connected to Redis successfully.")
except Exception as e:
    print(f"[VOICE AGENT CRITICAL ERROR] Could not connect to Redis: {e}")
    redis_client = None

http_client = httpx.AsyncClient(timeout=25.0)

# --- HANDLERS (Keep handle_call_start, handle_assistant_request, handle_call_end as they were) ---

def handle_call_start(message: dict):
    # ... (Keep existing code) ...
    call_id = message.get("call", {}).get("id")
    if not call_id or not redis_client:
        print("[VOICE AGENT ERROR] Call-start: No call_id or Redis client.")
        return Response(status_code=500)
    try:
        redis_client.set(call_id, json.dumps([]), ex=3600)
        print(f"[VOICE AGENT] Initialized Redis history for call: {call_id}")
        return Response(status_code=200)
    except Exception as e:
        print(f"[REDIS ERROR] handle_call_start: {e}")
        return Response(status_code=500)

async def handle_assistant_request(message: dict):
    # ... (Keep existing code for querying Ollama and updating Redis) ...
    call_id = message.get("call", {}).get("id")
    # Vapi sends the transcript *inside* the 'message' object for chat/completions
    # Check both potential locations for the transcript data
    transcript_data = message.get("transcript") # Original location
    if not transcript_data and message.get("messages"):
        # For chat/completions, the user message is often the last one in the list
        user_messages = [m for m in message.get("messages", []) if m.get("role") == "user"]
        if user_messages:
            transcript_data = user_messages[-1].get("content")

    transcript = transcript_data

    if not all([call_id, transcript, redis_client, settings.OLLAMA_API_ENDPOINT]):
        print("[VOICE AGENT ERROR] Assistant-request: Missing required data or config.")
        return {"error": "Assistant brain is misconfigured."}

    # 1. Retrieve history
    try:
        history_json = redis_client.get(call_id)
        history = json.loads(history_json) if history_json else []
    except Exception as e:
        print(f"[REDIS ERROR] handle_assistant_request (GET): {e}")
        return {"choices": [{"message": {"role": "assistant", "content": "I'm having trouble accessing my memory. Please repeat that."}}]} # Match OpenAI format

    # 2. Construct prompt
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    prompt = f"""You are a professional, polite, and efficient AI assistant...

Conversation History:
{formatted_history}

User: {transcript}
Assistant:"""

    payload = {
        "model": "llama3:8b",
        "prompt": prompt,
        "stream": False,
    }

    print(f"[VOICE AGENT] Sending prompt to Ollama for call {call_id}...")

    # 3. Call Ollama
    try:
        response = await http_client.post(settings.OLLAMA_API_ENDPOINT, json=payload)
        response.raise_for_status()
        assistant_response = response.json().get("response", "").strip()
        print(f"[VOICE AGENT] Received from Ollama: {assistant_response}")

    except httpx.RequestError as e:
        print(f"[VOICE AGENT ERROR] Could not connect to Ollama: {e}")
        # Return error in OpenAI format
        return {"choices": [{"message": {"role": "assistant", "content": "I apologize, I'm having connection issues. Could you repeat?"}}]}

    # 4. Update history
    try:
        history.append({"role": "User", "content": transcript})
        history.append({"role": "Assistant", "content": assistant_response})
        redis_client.set(call_id, json.dumps(history), ex=3600)
    except Exception as e:
        print(f"[REDIS ERROR] handle_assistant_request (SET): {e}")

    # 5. Return response in OpenAI format for Vapi Custom LLM
    return {"choices": [{"message": {"role": "assistant", "content": assistant_response}}]}


def handle_call_end(message: dict):
    # ... (Keep existing code) ...
    call_id = message.get("call", {}).get("id")
    customer_number = message.get("call", {}).get("customer", {}).get("number")
    # For call-end, the transcript might be in a different place
    final_transcript = message.get("transcript", "")
    if not final_transcript and message.get("analysis"): # Sometimes it's in the analysis block
        final_transcript = message.get("analysis", {}).get("transcript", "")
    if not final_transcript and message.get("artifact"): # Or maybe artifact
        final_transcript = message.get("artifact", {}).get("transcript", "")


    print(f"[VOICE AGENT] Call ended: {call_id}.") # Removed "Final transcript available." as it might be empty

    if customer_number and final_transcript:
        db: Session = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.phone_number == customer_number).first()
            if customer:
                print(f"[VOICE AGENT] Found customer ID {customer.customer_id}. Dispatching score_lead_task.")
                score_lead_task.delay(customer.customer_id, final_transcript)
            else:
                print(f"[VOICE AGENT] No existing customer found for {customer_number}. Not scoring lead.")
        finally:
            db.close()

    if call_id and redis_client:
        try:
            redis_client.delete(call_id)
            print(f"[VOICE AGENT] Cleared Redis history for call: {call_id}")
        except Exception as e:
            print(f"[REDIS ERROR] handle_call_end (DELETE): {e}")

    return Response(status_code=200)

# --- NEW: DEDICATED ENDPOINT FOR CUSTOM LLM ---
@router.post("/voice/webhook/chat/completions")
async def handle_chat_completions(request: Request):
    # --- ADD THIS LINE ---
    print(f"--- [{datetime.datetime.now()}] HIT /chat/completions ENDPOINT ---") 
    try:
        payload = await request.json()
        print(f"--- CHAT COMPLETIONS PAYLOAD RECEIVED ---\n{json.dumps(payload, indent=2)}\n---------------------------------")
        # ... (rest of the function remains the same) ...
        return await handle_assistant_request(payload) 
    except Exception as e:
        # --- ADD THIS LINE ---
        print(f"--- [{datetime.datetime.now()}] ERROR IN /chat/completions: {e} ---") 
        print(f"[VOICE AGENT ERROR] Failed to process chat completions: {e}")
        return Response(status_code=500, content=f"Internal Server Error: {str(e)}")


# --- UPDATED: ORIGINAL ENDPOINT FOR OTHER EVENTS ---
@router.post("/voice/webhook")
async def handle_vapi_webhook(request: Request):
    # --- ADD THIS LINE ---
    print(f"--- [{datetime.datetime.now()}] HIT BASE /webhook ENDPOINT ---") 
    try:
        payload = await request.json()
        print(f"--- GENERAL WEBHOOK PAYLOAD RECEIVED ---\n{json.dumps(payload, indent=2)}\n---------------------------------")
        # ... (rest of the function remains the same) ...
        message = payload.get("message", {})
        message_type = message.get("type")

        if message_type == "call-end" or message_type == "end-of-call-report":
             return handle_call_end(message)
        elif message_type == "call-start":
             return handle_call_start(message)
        
        return Response(status_code=200)

    except Exception as e:
         # --- ADD THIS LINE ---
        print(f"--- [{datetime.datetime.now()}] ERROR IN BASE /webhook: {e} ---")
        print(f"[VOICE AGENT ERROR] Failed to process general webhook: {e}")
        return Response(status_code=500, content=f"Internal Server Error: {str(e)}")