# Add this enhanced version that logs interactions
import json
import redis
import datetime
import traceback
import time
from fastapi import Request, Response
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.database import SessionLocal
from ...models.customer_model import Customer
from ...models.interaction_model import Interaction, CallLog
from ...schemas.customer_schema import CustomerCreate
from ...workflow.tasks import score_lead_task, analyze_interaction_task
# Import with full path for correct task registration
from ...workflow import tasks as workflow_tasks

try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("[VOICE AGENT] ✅ Connected to Redis successfully.")
except Exception as e:
    print(f"[VOICE AGENT] ❌ Could not connect to Redis: {e}")
    redis_client = None

def log_separator(title=""):
    print(f"\n{'='*70}")
    if title:
        print(f"  {title}")
        print(f"{'='*70}")

def handle_call_start(payload: dict) -> Response:
    """Handle call-start event from Vapi"""
    log_separator("CALL START EVENT")

    call_data = payload.get("call", {})
    call_id = call_data.get("id")
    customer_number = call_data.get("customer", {}).get("number")

    print(f"[CALL START] Call ID: {call_id}")
    print(f"[CALL START] Customer Number: {customer_number}")

    if not call_id:
        print("[CALL START] ❌ No call_id provided")
        return Response(status_code=400, content="Missing call_id")

    if redis_client:
        try:
            # Store call start info in Redis
            call_info = {
                "call_id": call_id,
                "customer_number": customer_number,
                "start_time": datetime.datetime.utcnow().isoformat()
            }
            redis_client.setex(
                f"call_active_{call_id}",
                3600,
                json.dumps(call_info)
            )
            print(f"[CALL START] ✅ Call info stored in Redis")
        except Exception as e:
            print(f"[CALL START] ❌ Redis error: {e}")

    return Response(status_code=200)


def handle_call_end(payload: dict) -> Response:
    """
    Enhanced call-end handler with interaction logging
    """
    log_separator("CALL END EVENT")

    report_data = payload
    call_data = report_data.get("call", {})
    call_id = call_data.get("id")
    if not call_id:
        call_id = report_data.get("id")

    customer_data = report_data.get("customer", {})
    customer_number = customer_data.get("number")

    # Extract transcript
    transcript = ""
    if "artifact" in report_data and isinstance(report_data["artifact"], dict):
        transcript = report_data["artifact"].get("transcript", "")
    if not transcript:
        transcript = report_data.get("transcript", "")
    if not transcript and "analysis" in report_data:
        transcript = report_data.get("analysis", {}).get("transcript", "")

    # Extract call metrics
    duration_seconds = call_data.get("duration", 0)
    call_status = call_data.get("status", "completed")

    print(f"[CALL END] Call ID: {call_id}")
    print(f"[CALL END] Customer Number: {customer_number}")
    print(f"[CALL END] Duration: {duration_seconds}s")
    print(f"[CALL END] Transcript Length: {len(transcript)} characters")

    # ⭐ FIX: Initialize IDs to None. They will only be set if the DB operations succeed.
    customer_id_for_task = None
    interaction_id = None

    if customer_number:
        db: Session = SessionLocal()
        try:
            # Find or create customer
            customer = db.query(Customer).filter(
                Customer.phone_number == customer_number
            ).first()

            _temp_customer_id = None
            if not customer:
                print(f"[CALL END] Creating new customer for: {customer_number}")
                new_customer_data = CustomerCreate(
                    phone_number=customer_number,
                    first_name="Unknown",
                    last_name="Caller"
                )
                customer = Customer(**new_customer_data.model_dump(exclude_unset=True))
                db.add(customer)
                db.flush()
                _temp_customer_id = customer.customer_id # Get ID before commit
                db.commit()
                db.refresh(customer)
                customer_id_for_task = _temp_customer_id # ⭐ Set ID only after successful commit
                print(f"[CALL END] ✅ Customer created: {customer_id_for_task}")
            else:
                customer_id_for_task = customer.customer_id
                print(f"[CALL END] ✅ Found existing customer: {customer_id_for_task}")

            # ⭐ NEW: Log the interaction
            if customer_id_for_task and transcript:
                interaction = Interaction(
                    customer_id=customer_id_for_task,
                    channel="Phone",
                    content=transcript,
                    outcome="Call completed",
                    interaction_timestamp=datetime.datetime.utcnow()
                )
                db.add(interaction)
                db.flush()
                _temp_interaction_id = interaction.interaction_id # Get ID before commit

                # Log call-specific details
                call_log = CallLog(
                    interaction_id=_temp_interaction_id,
                    call_sid=call_id,
                    duration_seconds=duration_seconds,
                    call_status=call_status,
                    call_direction="Inbound"
                )
                db.add(call_log)
                db.commit()
                interaction_id = _temp_interaction_id # ⭐ Set ID only after successful commit
                
                print(f"[CALL END] ✅ Interaction logged: {interaction_id}")

        except Exception as db_e:
            print(f"[CALL END] ❌ Database error: {db_e}")
            traceback.print_exc()
            if db.is_active:
                db.rollback()
            
            # ⭐ FIX: Ensure IDs are None if any DB error occurred
            customer_id_for_task = None
            interaction_id = None
        finally:
            db.close()

        # Trigger async tasks
        # This block will now ONLY run if customer_id_for_task is not None,
        # which means all database operations were successful.
        if customer_id_for_task and transcript:
            # ⭐ FIX: Removed time.sleep(1) - it blocks the main thread
            try:
                # Score the lead
                score_lead_task.apply_async(
                    args=[customer_id_for_task, transcript],
                    countdown=2
                )
                print(f"[CALL END] ✅ Lead scoring task queued")
                
                # ⭐ NEW: Analyze interaction for insights
                if interaction_id:
                    analyze_interaction_task.apply_async(
                        args=[interaction_id],
                        countdown=3
                    )
                    print(f"[CALL END] ✅ Interaction analysis task queued")
                    
            except Exception as task_e:
                print(f"[CALL END] ❌ Error queuing tasks: {task_e}")

    # Cleanup Redis
    if redis_client and call_id:
        try:
            redis_client.delete(f"call_active_{call_id}")
        except Exception as e:
            print(f"[CALL END] ⚠️ Redis cleanup error: {e}")

    log_separator()
    return Response(status_code=200)


async def vapi_server_webhook(request: Request):
    """Main webhook endpoint for Vapi events"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_separator(f"[{timestamp}] VAPI SERVER WEBHOOK")

    try:
        body_bytes = await request.body()
        if not body_bytes:
            return Response(status_code=200)
            
        payload = json.loads(body_bytes)
        message = payload.get("message", {})
        
        if not message:
            print("[WEBHOOK] ⚠️ Payload missing 'message' object")
            return Response(status_code=400)

        message_type = message.get("type", "unknown")
        print(f"[WEBHOOK] Event type: {message_type}")

        if message_type == "call-start":
            return handle_call_start(message)
        elif message_type in ["call-end", "end-of-call-report"]:
            return handle_call_end(message)
        else:
            return Response(status_code=200)

    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON")
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        traceback.print_exc()
        return Response(status_code=500)