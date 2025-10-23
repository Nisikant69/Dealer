# --- Imports needed at the top of handler.py ---
import json
import redis # If not already imported
import datetime
import traceback
import sys # For logging raw payload if needed
from fastapi import Request, Response, APIRouter
from sqlalchemy.orm import Session

# Adjust these imports based on your project structure
from ...core.config import settings
from ...core.database import SessionLocal
from ...models.customer_model import Customer
from ...schemas.customer_schema import CustomerCreate # Ensure you have this Pydantic schema
from ...workflow.tasks import score_lead_task


# --- Redis Client (ensure this is defined globally in handler.py) ---
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("[VOICE AGENT] ✅ Connected to Redis successfully.")
except Exception as e:
    print(f"[VOICE AGENT] ❌ Could not connect to Redis: {e}")
    redis_client = None

# --- Helper Function ---
def log_separator(title=""):
    """Print a visual separator for better log readability."""
    print(f"\n{'='*70}")
    if title:
        print(f"  {title}")
        print(f"{'='*70}")

# --- Handler Functions ---

def handle_call_start(payload: dict) -> Response:
    """
    Handle call-start event from Vapi.
    Initialize Redis state if needed for tracking active calls.
    """
    log_separator("CALL START EVENT")

    call_data = payload.get("call", {})
    call_id = call_data.get("id")
    customer_number = call_data.get("customer", {}).get("number")

    print(f"[CALL START] Call ID: {call_id}")
    print(f"[CALL START] Customer Number: {customer_number}")

    if not call_id:
        print("[CALL START] ❌ No call_id provided")
        return Response(status_code=400, content="Missing call_id")

    if not redis_client:
        print("[CALL START] ⚠️ Redis client not available, cannot track call state.")
        return Response(status_code=200) # Still acknowledge Vapi

    try:
        # Store basic call info or an active flag
        redis_client.set(f"call_active_{call_id}", "true", ex=3600) # Expires after 1 hour
        print(f"[CALL START] ✅ Marked call as active in Redis")
        return Response(status_code=200)
    except Exception as e:
        print(f"[CALL START] ❌ Redis error: {e}")
        return Response(status_code=200) # Still acknowledge Vapi even if Redis fails here


def handle_call_end(payload: dict) -> Response:
    """
    Handle call-end or end-of-call-report event from Vapi.
    Extract transcript, add customer if new, trigger lead scoring, and cleanup.
    ** Expects the 'message' object from the raw Vapi webhook payload **
    """
    log_separator("CALL END EVENT")

    # --- Optional: Keep this DEBUG logging temporarily ---
    # print("[CALL END DEBUG] Raw payload received by handle_call_end:")
    # try:
    #     print(json.dumps(payload, indent=2), file=sys.stderr)
    # except Exception as log_e:
    #     print(f"[CALL END DEBUG] Error logging payload: {log_e}")
    # print("[CALL END DEBUG] --- End raw payload ---")
    # --- END DEBUG ---

    report_data = payload # Assumes vapi_server_webhook passed the 'message' object

    # Extract Call ID and Customer Number safely
    call_id = report_data.get("call", {}).get("id")
    # If call_id is still None, try getting it from the top level of the message object (less common)
    if not call_id:
         call_id = report_data.get("id") # Check if call ID might be here

    customer_data = report_data.get("customer", {})
    customer_number = customer_data.get("number")

    # --- Transcript Extraction Logic ---
    transcript = ""
    # Check primary location: message['artifact']['transcript']
    if "artifact" in report_data and isinstance(report_data["artifact"], dict):
        transcript = report_data["artifact"].get("transcript", "")
        # print(f"[CALL END DEBUG] Found transcript in artifact: {bool(transcript)}") # Optional debug

    # Fallback 1: Check message['transcript']
    if not transcript:
        transcript = report_data.get("transcript", "")
        # print(f"[CALL END DEBUG] Found transcript at message top level: {bool(transcript)}") # Optional debug

    # Fallback 2: Check message['analysis']['transcript']
    if not transcript and "analysis" in report_data and isinstance(report_data["analysis"], dict):
        transcript = report_data["analysis"].get("transcript", "")
        # print(f"[CALL END DEBUG] Found transcript in analysis: {bool(transcript)}") # Optional debug
    # --- END Transcript Logic ---

    print(f"[CALL END] Call ID: {call_id}")
    print(f"[CALL END] Customer Number: {customer_number}")
    print(f"[CALL END] Transcript Length: {len(transcript)} characters")

    # --- Add Customer if New & Trigger Lead Scoring ---
    customer_id_for_task = None

    if customer_number:
        print(f"[CALL END] Looking up customer with phone: {customer_number}")
        db: Session = SessionLocal()
        try:
            customer = db.query(Customer).filter(
                Customer.phone_number == customer_number
            ).first()

            if customer:
                print(f"[CALL END] ✅ Found existing customer: {customer.customer_id}")
                customer_id_for_task = customer.customer_id
            else:
                print(f"[CALL END] ⚠️ No customer found for number: {customer_number}. Creating new customer.")
                try:
                    # !! IMPORTANT !! Ensure CustomerCreate schema ONLY requires phone_number
                    # If it requires other fields (like first_name), you MUST provide defaults
                    # or make them optional in the schema.
                    new_customer_data = CustomerCreate(
                        phone_number=customer_number
                        # Add default/optional values here if needed by your schema:
                        # first_name="Unknown",
                        # last_name="Caller",
                        # email=None,
                        )
                    new_customer = Customer(**new_customer_data.model_dump(exclude_unset=True)) # Exclude unset optional fields
                    db.add(new_customer)
                    db.commit()
                    db.refresh(new_customer)
                    customer_id_for_task = new_customer.customer_id
                    print(f"[CALL END] ✅ Successfully created new customer: {customer_id_for_task}")
                except Exception as create_e:
                    db.rollback()
                    print(f"[CALL END] ❌ Error creating new customer: {create_e}")
                    # Log the validation error details if it's a Pydantic error
                    if "validation error for CustomerCreate" in str(create_e):
                         print(f"[CALL END] CustomerCreate Schema Validation Error Details: {create_e}")
                    # customer_id_for_task remains None

        except Exception as db_e:
            print(f"[CALL END] ❌ Database lookup/connection error: {db_e}")
            if db.is_active: # Check if rollback is safe
                db.rollback()
        finally:
            db.close()

        # Trigger scoring task ONLY if we have a customer ID and a transcript
        if customer_id_for_task and transcript:
            print(f"[CALL END] Triggering lead scoring task for customer: {customer_id_for_task}...")
            try:
                score_lead_task.delay(customer_id_for_task, transcript)
                print(f"[CALL END] ✅ Lead scoring task queued")
            except Exception as task_e:
                 print(f"[CALL END] ❌ Error queuing lead scoring task: {task_e}")
        elif not transcript:
             print(f"[CALL END] ⚠️ No transcript available in payload, cannot score.")
        elif not customer_id_for_task:
             print(f"[CALL END] ⚠️ Could not find or create customer, cannot score.")

    else: # Case where customer_number was missing
        print(f"[CALL END] ⚠️ No customer number provided in payload, cannot add customer or score.")

    # --- Cleanup Redis ---
    if redis_client and call_id:
        try:
            # Delete the active call marker or any other keys related to call_id
            deleted_count = redis_client.delete(f"call_active_{call_id}") # Matches key set in handle_call_start
            if deleted_count > 0:
                 print(f"[CALL END] ✅ Cleared call state from Redis for call: {call_id}")
            # else: # This log can be noisy if call_start failed or key expired
                 # print(f"[CALL END] ⚠️ No call state found in Redis to clear for call: {call_id}")
        except Exception as e:
            print(f"[CALL END] ⚠️ Redis cleanup error: {e}")

    log_separator()
    return Response(status_code=200) # Always acknowledge Vapi


# --- Main Webhook Router Function ---

async def vapi_server_webhook(request: Request):
    """
    Server webhook endpoint for Vapi lifecycle events (call start/end etc.).
    Receives the raw payload from Vapi, extracts the inner 'message' object,
    and routes based on message type.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_separator(f"[{timestamp}] VAPI SERVER WEBHOOK")

    try:
        # Check for empty body before parsing JSON
        body_bytes = await request.body()
        if not body_bytes:
            print("[WEBHOOK] Received empty request body. Acknowledging with 200 OK.")
            return Response(status_code=200)
        payload = json.loads(body_bytes)

        # Vapi wraps lifecycle events in a "message" object - THIS IS KEY
        message = payload.get("message", {})
        if not message:
             print("[WEBHOOK] ⚠️ Payload missing 'message' object. Raw payload:")
             print(json.dumps(payload, indent=2))
             return Response(status_code=400, content="Invalid Vapi payload: Missing 'message' object")

        message_type = message.get("type", "unknown")

        print(f"[WEBHOOK] Event type: {message_type}")

        # Route to appropriate handler, passing the INNER message object
        if message_type == "call-start":
            result = handle_call_start(message)
        elif message_type in ["call-end", "end-of-call-report"]:
            result = handle_call_end(message) # Pass the 'message' object here
        else:
            # Gracefully ignore other events Vapi might send
            print(f"[WEBHOOK] Unhandled or irrelevant event type: {message_type}")
            # Optional: Log the payload for unhandled types during debugging
            # print("[WEBHOOK] Unhandled Payload:")
            # print(json.dumps(payload, indent=2))
            print(f"[WEBHOOK] Acknowledging with 200 OK")
            result = Response(status_code=200)

        return result

    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON received on server webhook.")
        return Response(status_code=400, content="Invalid JSON")
    except Exception as e:
        print(f"[ERROR] Unhandled exception in server webhook endpoint: {e}")
        traceback.print_exc()
        return Response(status_code=500, content=f"Internal Server Error: {str(e)}")