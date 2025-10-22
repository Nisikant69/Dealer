import requests
from fastapi import Request, Response
from sqlalchemy.orm import Session
import json

from ...core.config import settings
from ...core.database import SessionLocal
from ...models.customer_model import Customer
from ...workflow.tasks import score_lead_task

# WARNING: This is a simple in-memory dictionary for conversation history.
# It is NOT suitable for production. For a real system, this state
# must be managed in a persistent store like Redis or your database.
conversation_history = {}

async def handle_vapi_webhook(request: Request):
    """
    Handles all incoming webhook events from the Vapi voice platform.
    This is the core logic of the voice agent.
    """
    try:
        payload = await request.json()

        print(f"--- RAW VAPI PAYLOAD RECEIVED ---\n{json.dumps(payload, indent=2)}\n---------------------------------")

        message = payload.get("message", {})
        message_type = message.get("type")

        if message_type == "voice-input":
            return await handle_assistant_request(message)
        elif message_type == "hang":
            return handle_call_end(message)
        elif message_type == "status-update":
            return handle_call_start(message)
        else:
            # Acknowledge other event types without taking action.
            return Response(status_code=200)

    except Exception as e:
        print(f"[VOICE AGENT ERROR] Failed to process webhook: {e}")
        return Response(status_code=500, content=f"Internal Server Error: {str(e)}")

def handle_call_start(message: dict):
    call_id = message.get("call", {}).get("id")
    if call_id:
        conversation_history[call_id] = []
        print(f"[VOICE AGENT] Initialized history for call: {call_id}")
    return Response(status_code=200)

async def handle_assistant_request(message: dict):
    call_id = message.get("call", {}).get("id")
    transcript = message.get("transcript")

    if not settings.OLLAMA_API_ENDPOINT:
        print("[VOICE AGENT ERROR] OLLAMA_API_ENDPOINT is not configured.")
        return {"error": "Assistant brain is not configured."}

    # Retrieve and format conversation history
    history = conversation_history.get(call_id, [])
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    # Construct the prompt for the local LLM. This is a critical step.
    prompt = f"""You are a professional, polite, and efficient AI assistant for a high-end luxury car dealership. Your goal is to qualify the lead by understanding their interest and, if appropriate, to schedule a showroom appointment or test drive. Keep your responses concise for a voice conversation.

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
    try:
        response = requests.post(settings.OLLAMA_API_ENDPOINT, json=payload, timeout=25)
        response.raise_for_status()
        assistant_response = response.json().get("response", "").strip()
        print(f"[VOICE AGENT] Received from Ollama: {assistant_response}")

        # Update history
        history.append({"role": "User", "content": transcript})
        history.append({"role": "Assistant", "content": assistant_response})
        conversation_history[call_id] = history

        # Return the response for Vapi to convert to speech
        return {"assistant": {"role": "assistant", "content": assistant_response}}
    except requests.RequestException as e:
        print(f"[VOICE AGENT ERROR] Could not connect to Ollama: {e}")
        return {"assistant": {"role": "assistant", "content": "I apologize, I'm having a momentary connection issue. Could you please repeat that?"}}

def handle_call_end(message: dict):
    call_id = message.get("call", {}).get("id")
    customer_number = message.get("call", {}).get("customer", {}).get("number")
    final_transcript = message.get("transcript", "")

    print(f"[VOICE AGENT] Call ended: {call_id}. Final transcript available.")

    if customer_number and final_transcript:
        db: Session = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.phone_number == customer_number).first()
            if customer:
                print(f"[VOICE AGENT] Found customer ID {customer.customer_id}. Dispatching score_lead_task.")
                score_lead_task.delay(customer.customer_id, final_transcript)
            else:
                # This is a business decision. For now, we only score existing customers.
                print(f"[VOICE AGENT] No existing customer found for {customer_number}. Not scoring lead.")
        finally:
            db.close()

    # Clean up state
    if call_id in conversation_history:
        del conversation_history[call_id]
        print(f"[VOICE AGENT] Cleared history for call: {call_id}")
    
    return Response(status_code=200)
