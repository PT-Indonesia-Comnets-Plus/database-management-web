from fpdf import FPDF
from io import BytesIO
from datetime import datetime


def generate_receipt(order_data):
    pdf = FPDF()
    pdf.add_page()

    # Set title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Receipt', 0, 1, 'C')

    # Add order details
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, datetime.now().strftime("%d-%m-%Y %H:%M:%S"), 0, 1, 'R')
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Buyer: {order_data['buyer']}", 0, 1)
    pdf.cell(0, 10, f"Product: {order_data['product_name']}", 0, 1)
    pdf.cell(0, 10, f"Store: {order_data['store']}", 0, 1)
    pdf.cell(0, 10, f"Quantity: {order_data['quantity']}", 0, 1)
    pdf.cell(0, 10, f"Payment Method: {order_data['payment_method']}", 0, 1)
    pdf.cell(0, 10, f"Price per Item: {order_data['price']}", 0, 1)
    total_price = order_data['quantity'] * order_data['price']
    pdf.cell(0, 10, f"Total Price: {total_price}", 0, 1)

    # Save the PDF to a byte stream
    pdf_output = pdf.output(dest='S').encode('latin1')
    pdf_stream = BytesIO(pdf_output)

    return pdf_stream
