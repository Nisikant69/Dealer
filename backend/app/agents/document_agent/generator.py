import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from sqlalchemy.orm import Session

from ...models.customer_model import Customer
from ...models.vehicle_model import Vehicle
from ...models.document_model import Document

# Path to the templates directory
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
# Path to save generated PDFs
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'generated_documents')

def create_invoice_pdf(db: Session, customer_id: int, vehicle_id: int) -> str:
    """
    Generates an invoice PDF for a given customer and vehicle.
    Returns the path to the generated file.
    """
    # 1. Fetch data from the database
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()

    if not customer or not vehicle:
        raise ValueError("Customer or Vehicle not found")

    # 2. Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template('invoice_template.html')

    # 3. Prepare data and calculations for the template
    gst_rate = 18.0
    gst_amount = float(vehicle.base_price) * (gst_rate / 100)
    total_price = float(vehicle.base_price) + gst_amount

    context = {
        "customer": customer,
        "vehicle": vehicle,
        "invoice_number": f"INV-{datetime.now().strftime('%Y%m%d')}-{customer_id}",
        "issue_date": datetime.now().strftime("%d-%b-%Y"),
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "total_price": total_price,
    }

    # 4. Render the HTML template
    html_out = template.render(context)

    # 5. Define output path and ensure directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_name = f"{context['invoice_number']}.pdf"
    output_path = os.path.join(OUTPUT_DIR, file_name)

    # 6. Convert HTML to PDF
    with open(output_path, "w+b") as pdf_file:
        pisa_status = pisa.CreatePDF(html_out.encode('utf-8'), dest=pdf_file, encoding='utf-8')

    if pisa_status.err:
        raise IOError("PDF generation failed")

    # 7. Save document record to the database
    new_document = Document(
        customer_id=customer_id,
        document_type="Invoice",
        file_path=output_path
    )
    db.add(new_document)
    db.commit()

    print(f"Successfully generated PDF: {output_path}")
    return output_path