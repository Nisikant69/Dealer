from ..core.celery_app import celery_app
from ..core.database import SessionLocal
from ..agents.document_agent.generator import create_invoice_pdf
from ..agents.communication_agent.email_handler import send_email_with_attachment
from ..models.customer_model import Customer
from ..models.interaction_model import Interaction
from ..agents.lead_intelligence_agent.scoring import score_lead_from_text
from ..agents.lead_intelligence_agent.analyzer import analyze_conversation_sentiment, extract_key_intents
import time
import traceback
from datetime import datetime, timedelta

@celery_app.task(name="test_celery_task")
def test_celery_task(word: str) -> str:
    print(f"Celery task received word: {word}")
    return f"Test task successful with word: {word}"


@celery_app.task(name="generate_invoice_task")
def generate_invoice_task(customer_id: int, vehicle_id: int):
    """Generate invoice PDF and trigger email"""
    db = SessionLocal()
    try:
        pdf_path = create_invoice_pdf(db, customer_id, vehicle_id)
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        
        if not customer or not customer.email:
            raise ValueError(f"No customer email for customer_id: {customer_id}")

        send_invoice_email_task.delay(customer.email, pdf_path)
        return f"Invoice generated and email queued for {customer.email}"

    except Exception as e:
        print(f"Error in generate_invoice_task: {e}")
        traceback.print_exc()
        raise
    finally:
        db.close()


@celery_app.task(name="send_invoice_email_task")
def send_invoice_email_task(recipient_email: str, attachment_path: str):
    """Send email with invoice attachment"""
    subject = "Your Invoice from Luxury Auto Group"
    body = "Dear Customer,\n\nPlease find your invoice attached.\n\nThank you for your business.\n\nBest regards,\nLuxury Auto Group"
    
    try:
        send_email_with_attachment(recipient_email, subject, body, attachment_path)
        return f"Email successfully sent to {recipient_email}"
    except Exception as e:
        print(f"Failed to send email: {e}")
        traceback.print_exc()
        raise


@celery_app.task(name="score_lead_task", bind=True, max_retries=3)
def score_lead_task(self, customer_id: int, input_text: str):
    """Score a lead based on conversation text"""
    print(f"[SCORE_LEAD_TASK] ▶️ Starting for customer_id: {customer_id}")
    
    db = SessionLocal()
    try:
        if self.request.retries == 0:
            print(f"[SCORE_LEAD_TASK] Initial delay for DB consistency...")
            time.sleep(1)
        
        # Score the lead
        lead_status = score_lead_from_text(input_text)
        print(f"[SCORE_LEAD_TASK] ✅ Lead status: {lead_status}")

        # Fetch and update customer
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()

        if not customer:
            error_msg = f"Customer not found: {customer_id}"
            print(f"[SCORE_LEAD_TASK] ❌ {error_msg}")
            
            if self.request.retries < self.max_retries:
                raise self.retry(exc=ValueError(error_msg), countdown=5)
            else:
                raise ValueError(error_msg)

        old_status = customer.customer_type
        customer.customer_type = lead_status
        db.add(customer)
        db.commit()
        db.refresh(customer)

        print(f"[SCORE_LEAD_TASK] ✅ Updated {customer_id}: {old_status} → {lead_status}")
        
        return {
            "customer_id": customer_id,
            "previous_status": old_status,
            "new_status": lead_status
        }

    except Exception as e:
        db.rollback()
        print(f"[SCORE_LEAD_TASK] ❌ Error: {e}")
        traceback.print_exc()
        
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 5
            raise self.retry(exc=e, countdown=countdown)
        else:
            raise
    finally:
        db.close()


@celery_app.task(name="analyze_interaction_task", bind=True, max_retries=2)
def analyze_interaction_task(self, interaction_id: int):
    """
    ⭐ NEW TASK: Analyze interaction for sentiment, intent, and insights
    """
    print(f"[ANALYZE_INTERACTION] ▶️ Analyzing interaction: {interaction_id}")
    
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(
            Interaction.interaction_id == interaction_id
        ).first()

        if not interaction:
            error_msg = f"Interaction not found: {interaction_id}"
            print(f"[ANALYZE_INTERACTION] ❌ {error_msg}")
            
            if self.request.retries < self.max_retries:
                raise self.retry(exc=ValueError(error_msg), countdown=5)
            raise ValueError(error_msg)

        content = interaction.content or ""
        if not content:
            print(f"[ANALYZE_INTERACTION] ⚠️ No content to analyze")
            return {"message": "No content available"}

        # Analyze sentiment
        sentiment = analyze_conversation_sentiment(content)
        print(f"[ANALYZE_INTERACTION] Sentiment: {sentiment}")

        # Extract intents (e.g., wants test drive, pricing inquiry, etc.)
        intents = extract_key_intents(content)
        print(f"[ANALYZE_INTERACTION] Intents: {intents}")

        # Generate summary (simple version - you can enhance with LLM)
        summary = generate_interaction_summary(content)
        print(f"[ANALYZE_INTERACTION] Summary generated")

        # Update interaction record
        interaction.sentiment = sentiment
        interaction.summary = summary
        interaction.outcome = determine_outcome_from_intents(intents)
        
        db.add(interaction)
        db.commit()
        
        print(f"[ANALYZE_INTERACTION] ✅ Interaction {interaction_id} analyzed")
        
        # Trigger follow-up actions based on intent
        if "test_drive" in intents:
            schedule_followup_task.delay(interaction.customer_id, "test_drive_confirmation")
        if "pricing" in intents:
            schedule_followup_task.delay(interaction.customer_id, "send_pricing")

        return {
            "interaction_id": interaction_id,
            "sentiment": sentiment,
            "intents": intents,
            "summary": summary[:100]
        }

    except Exception as e:
        db.rollback()
        print(f"[ANALYZE_INTERACTION] ❌ Error: {e}")
        traceback.print_exc()
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)
        raise
    finally:
        db.close()


@celery_app.task(name="schedule_followup_task")
def schedule_followup_task(customer_id: int, followup_type: str):
    """
    ⭐ NEW TASK: Schedule automated follow-ups based on customer interactions
    """
    print(f"[SCHEDULE_FOLLOWUP] ▶️ Customer: {customer_id}, Type: {followup_type}")
    
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        
        if not customer:
            print(f"[SCHEDULE_FOLLOWUP] ❌ Customer not found: {customer_id}")
            return
        
        # Determine follow-up timing and content based on type
        followup_config = {
            "test_drive_confirmation": {
                "delay_hours": 2,
                "subject": "Schedule Your Test Drive",
                "template": "test_drive_followup"
            },
            "send_pricing": {
                "delay_hours": 1,
                "subject": "Pricing Information You Requested",
                "template": "pricing_info"
            },
            "post_call_thankyou": {
                "delay_hours": 0.5,
                "subject": "Thank You for Your Interest",
                "template": "post_call_thankyou"
            },
            "nurture_warm_lead": {
                "delay_hours": 24,
                "subject": "Exclusive Luxury Vehicle Updates",
                "template": "nurture_campaign"
            }
        }
        
        config = followup_config.get(followup_type)
        if not config:
            print(f"[SCHEDULE_FOLLOWUP] ⚠️ Unknown followup type: {followup_type}")
            return
        
        # Schedule email to be sent after delay
        delay_seconds = int(config["delay_hours"] * 3600)
        
        if customer.email:
            send_followup_email_task.apply_async(
                args=[customer.email, config["subject"], config["template"], customer_id],
                countdown=delay_seconds
            )
            print(f"[SCHEDULE_FOLLOWUP] ✅ Email scheduled in {config['delay_hours']} hours")
        else:
            print(f"[SCHEDULE_FOLLOWUP] ⚠️ No email for customer {customer_id}")
        
        return {
            "customer_id": customer_id,
            "followup_type": followup_type,
            "scheduled_in_hours": config["delay_hours"]
        }

    except Exception as e:
        print(f"[SCHEDULE_FOLLOWUP] ❌ Error: {e}")
        traceback.print_exc()
    finally:
        db.close()


@celery_app.task(name="send_followup_email_task")
def send_followup_email_task(recipient_email: str, subject: str, template_name: str, customer_id: int):
    """
    ⭐ NEW TASK: Send personalized follow-up emails
    """
    print(f"[SEND_FOLLOWUP] ▶️ Sending {template_name} to {recipient_email}")
    
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        
        if not customer:
            print(f"[SEND_FOLLOWUP] ❌ Customer not found: {customer_id}")
            return
        
        # Generate personalized email body based on template
        body = generate_email_from_template(template_name, customer)
        
        # Send email (without attachment)
        send_email_with_attachment(recipient_email, subject, body, attachment_path=None)
        
        print(f"[SEND_FOLLOWUP] ✅ Email sent to {recipient_email}")
        
        return {
            "recipient": recipient_email,
            "template": template_name,
            "status": "sent"
        }

    except Exception as e:
        print(f"[SEND_FOLLOWUP] ❌ Error: {e}")
        traceback.print_exc()
        raise
    finally:
        db.close()


@celery_app.task(name="daily_lead_nurture_task")
def daily_lead_nurture_task():
    """
    ⭐ NEW TASK: Daily batch job to nurture warm leads
    Run this via Celery Beat (periodic task scheduler)
    """
    print(f"[DAILY_NURTURE] ▶️ Starting daily lead nurture job")
    
    db = SessionLocal()
    try:
        # Find warm leads that haven't been contacted in 3+ days
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        
        # Query for warm leads with recent interactions
        warm_leads = db.query(Customer).filter(
            Customer.customer_type == 'Warm Lead'
        ).all()
        
        nurtured_count = 0
        for customer in warm_leads:
            # Check last interaction
            last_interaction = db.query(Interaction).filter(
                Interaction.customer_id == customer.customer_id
            ).order_by(Interaction.interaction_timestamp.desc()).first()
            
            if last_interaction and last_interaction.interaction_timestamp < three_days_ago:
                # Schedule nurture email
                if customer.email:
                    schedule_followup_task.delay(customer.customer_id, "nurture_warm_lead")
                    nurtured_count += 1
        
        print(f"[DAILY_NURTURE] ✅ Scheduled nurture emails for {nurtured_count} leads")
        
        return {
            "total_warm_leads": len(warm_leads),
            "nurtured": nurtured_count
        }

    except Exception as e:
        print(f"[DAILY_NURTURE] ❌ Error: {e}")
        traceback.print_exc()
        raise
    finally:
        db.close()


# ========== Helper Functions ==========

def generate_interaction_summary(content: str, max_length: int = 200) -> str:
    """Generate a brief summary of the interaction"""
    if not content:
        return "No content available"
    
    # Simple summary: first sentence or first N chars
    sentences = content.split('.')
    if sentences:
        summary = sentences[0].strip() + '.'
        if len(summary) > max_length:
            summary = summary[:max_length] + '...'
        return summary
    
    return content[:max_length] + '...' if len(content) > max_length else content


def determine_outcome_from_intents(intents: list) -> str:
    """Determine interaction outcome based on extracted intents"""
    if "test_drive" in intents:
        return "Test drive interest expressed"
    elif "pricing" in intents:
        return "Pricing inquiry"
    elif "appointment" in intents:
        return "Appointment requested"
    elif "purchase_ready" in intents:
        return "Ready to purchase"
    else:
        return "General inquiry"


def generate_email_from_template(template_name: str, customer: Customer) -> str:
    """Generate email body from template"""
    first_name = customer.first_name or "Valued Customer"
    
    templates = {
        "test_drive_followup": f"""Dear {first_name},

Thank you for your interest in test driving one of our luxury vehicles.

We would be delighted to arrange a personalized test drive experience at your convenience. Our showroom offers a private, white-glove service to ensure you have the perfect environment to experience the vehicle.

Please reply to this email or call us at your earliest convenience to schedule your appointment.

Best regards,
Luxury Auto Group
""",
        "pricing_info": f"""Dear {first_name},

Thank you for your inquiry about our luxury vehicle collection.

As requested, I'm pleased to share detailed pricing information with you. Our team can also discuss flexible financing options and exclusive offers available for our valued clients.

Would you like to schedule a private consultation to discuss your specific requirements?

Best regards,
Luxury Auto Group
""",
        "post_call_thankyou": f"""Dear {first_name},

Thank you for taking the time to speak with us today.

It was a pleasure learning about your automotive preferences. We're committed to helping you find the perfect luxury vehicle that matches your lifestyle and expectations.

If you have any additional questions, please don't hesitate to reach out.

Best regards,
Luxury Auto Group
""",
        "nurture_campaign": f"""Dear {first_name},

We wanted to share some exciting updates from Luxury Auto Group.

Our latest collection includes exclusive models that align with the preferences you shared with us. We would be honored to provide you with a private viewing.

Your satisfaction is our priority, and we're here whenever you're ready to explore further.

Best regards,
Luxury Auto Group
"""
    }
    
    return templates.get(template_name, f"Dear {first_name},\n\nThank you for your interest in Luxury Auto Group.\n\nBest regards,\nLuxury Auto Group")