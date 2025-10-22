from ..core.celery_app import celery_app
from ..core.database import SessionLocal # <-- Import SessionLocal
from ..agents.document_agent.generator import create_invoice_pdf
from ..agents.communication_agent.email_handler import send_email_with_attachment
from ..models.customer_model import Customer
from ..agents.lead_intelligence_agent.scoring import score_lead_from_text # Import the new scoring function


@celery_app.task(name="test_celery_task")
def test_celery_task(word: str) -> str:
    print(f"Celery task received word: {word}")
    return f"Test task successful with word: {word}"

# --- NEW TASK ---
@celery_app.task(name="generate_invoice_task")
def generate_invoice_task(customer_id: int, vehicle_id: int):
    """
    Celery task to generate an invoice PDF and then trigger the email task.
    """
    db = SessionLocal()
    try:
        # Step 1: Generate the PDF
        pdf_path = create_invoice_pdf(db, customer_id, vehicle_id)
        
        # Step 2: Fetch the customer's email
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not customer or not customer.email:
            raise ValueError(f"Could not find customer or customer email for customer_id: {customer_id}")

        # Step 3: Trigger the email task by chaining it.
        # .delay() is a shortcut for .apply_async()
        send_invoice_email_task.delay(customer.email, pdf_path)

        return f"Invoice generated and email task queued for {customer.email}"

    except Exception as e:
        print(f"Error in generate_invoice_task: {e}")
        raise
    finally:
        db.close()

@celery_app.task(name="send_invoice_email_task")
def send_invoice_email_task(recipient_email: str, attachment_path: str):
    """
    Celery task to send an email with the generated invoice.
    """
    subject = "Your Invoice from Luxury Auto Group"
    body = "Dear Customer,\n\nPlease find your invoice attached.\n\nThank you for your business.\n\nBest regards,\nLuxury Auto Group"
    try:
        send_email_with_attachment(recipient_email, subject, body, attachment_path)
        return f"Email successfully sent to {recipient_email}"
    except Exception as e:
        print(f"Celery task failed to send email. Error: {e}")
        # Celery can be configured to retry tasks on failure
        raise

@celery_app.task(name="score_lead_task", bind=True) # Added bind=True for retry
def score_lead_task(self, customer_id: int, input_text: str): # Added self for retry
    """
    Celery task to score a lead based on input text and update the customer record.
    """
    print(f"Received score_lead_task for customer_id: {customer_id}")
    db = SessionLocal()
    try:
        # Step 1: Score the lead using the imported function
        lead_status = score_lead_from_text(input_text)
        print(f"Determined lead status: {lead_status}")

        # Step 2: Fetch the customer record
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()

        if not customer:
            raise ValueError(f"Customer not found for customer_id: {customer_id}")

        # Step 3: Update the customer's type/status
        customer.customer_type = lead_status
        db.add(customer) # Add the updated object back to the session
        db.commit()
        db.refresh(customer) # Refresh to confirm the change

        print(f"Successfully updated customer {customer_id} status to {lead_status}")
        return f"Customer {customer_id} updated to {lead_status}"

    except Exception as e:
        db.rollback() # Rollback on error
        print(f"Error scoring lead for customer {customer_id}: {e}")
        # Retry the task on failure after 60 seconds
        self.retry(exc=e, countdown=60) # Added retry logic
    finally:
        db.close()