import streamlit as st
import fpdf
import os
import sqlite3
import time
from datetime import datetime, timedelta

# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 1

if 'invoice_data' not in st.session_state:
    st.session_state.invoice_data = {}

if 'pdf_file' not in st.session_state:
    st.session_state.pdf_file = None

if 'clear_confirm' not in st.session_state:
    st.session_state.clear_confirm = False

if 'confPass' not in st.session_state:
    st.session_state.confPass = ''

if 'apply_vat' not in st.session_state:
    st.session_state.apply_vat = False

# Database setup
def init_db():
    conn = sqlite3.connect('invoices.db')
    c = conn.cursor()
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS invoices
             (id INTEGER PRIMARY KEY, invoice_number TEXT, client_name TEXT, client_address TEXT, 
             client_contact TEXT, services TEXT, signed_by TEXT, pdf_path TEXT)''')
    # Add date_created column if it doesn't exist
    c.execute("PRAGMA table_info(invoices)")
    columns = [info[1] for info in c.fetchall()]
    if 'date_created' not in columns:
        c.execute('''ALTER TABLE invoices ADD COLUMN date_created DATE''')
    conn.commit()
    conn.close()

def save_invoice_data(invoice_data, pdf_path):
    conn = sqlite3.connect('invoices.db')
    c = conn.cursor()
    c.execute('''INSERT INTO invoices (invoice_number, client_name, client_address, client_contact, services, signed_by, pdf_path, date_created)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
           (invoice_data['invoice_number'], invoice_data['client_name'], invoice_data['client_address'],
            invoice_data['client_contact'], str(invoice_data['services']), invoice_data['signed_by'], pdf_path, datetime.now().date()))
    conn.commit()
    conn.close()

def get_all_invoices(limit=10):
    conn = sqlite3.connect('invoices.db')
    c = conn.cursor()
    c.execute('SELECT * FROM invoices ORDER BY date_created DESC, id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_daily_invoice_count():
    conn = sqlite3.connect('invoices.db')
    c = conn.cursor()
    today = datetime.now().date()
    c.execute('SELECT COUNT(*) FROM invoices WHERE date_created = ?', (today,))
    count = c.fetchone()[0]
    conn.close()
    return count

# Initialize the database
init_db()

# Helper function to create PDF
def create_pdf(invoice_data, apply_vat):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Add custom font
    if not os.path.exists('calibri.ttf'):
        st.error("Calibri font file not found.")
        return None

    pdf.add_font('Calibri', '', 'calibri.ttf', uni=True)
    pdf.set_font("Calibri", size=12)
    
    # Get the dimensions of the page
    page_width = pdf.w
    page_height = pdf.h

    # Add a black border of 2px (0.5mm) on the corners of the PDF
    pdf.set_line_width(0.5)  # 0.5 mm line width
    pdf.set_draw_color(0, 0, 0)  # Black color
    pdf.rect(1, 1, page_width - 2, page_height - 2)  # Rectangle position and size

    # Add company details on the left
    pdf.image('logo.png', x=10, y=8, w=40)  # Assuming logo.png is your logo file
    pdf.set_xy(10, 25)
    pdf.cell(100, 5, txt="Aiwa Media Group", ln=True, align="L")
    pdf.cell(100, 5, txt="Formerly known as AiwaDigitals", ln=True, align="L")
    pdf.cell(100, 5, txt="HGRW+VMV, 3711 Way, Muscat, Oman", ln=True, align="L")
    
    # Add client details on the right
    pdf.set_xy(90, 10)
    pdf.cell(120, 10, txt=f"Invoice Number: {invoice_data['invoice_number']}   ", ln=True, align="R")
    pdf.cell(200, 5, txt=f"Client Name: {invoice_data['client_name']}   ", ln=True, align="R")
    pdf.cell(200, 5, txt=f"Client Address: {invoice_data['client_address']}   ", ln=True, align="R")
    pdf.cell(200, 5, txt=f"Client Contact: {invoice_data['client_contact']}   ", ln=True, align="R")

    # Calculate the last day of the current month
    now = datetime.now()
    next_month = now.replace(day=28) + timedelta(days=4)  # this will never fail
    last_day_of_month = next_month - timedelta(days=next_month.day)
    last_day_str = last_day_of_month.strftime("%d %B %y")

    pdf.cell(200, 10, txt=f"Last Billable Date: {last_day_str}   ", ln=True, align="R")
    
    pdf.cell(200, 10, txt="", ln=True)  # empty line

    # Add divider image
    # if os.path.exists('divider.png'):
    #   y_position = pdf.get_y()  # Get the current y position
    #   pdf.image('divider.png', x=0, y=pdf.get_y() - 110, w=200)  # Adjust 'x', 'y', and 'w' as needed

    # Add dynamic paragraph
    paragraph = f"Dear {invoice_data['client_name']},\n\n" \
          "We hope this message finds you well. We are writing to inform you that a new invoice for the services rendered by Aiwa Media Group is now available. The invoice reflects the recent transactions and services provided, and it is ready for your review and payment."

    pdf.set_xy(10, pdf.get_y() + 5)
    pdf.multi_cell(180, 8, txt=paragraph)  # Use 8 as the height for reduced line spacing

    # Add services table
    pdf.set_xy(10, pdf.get_y() + 10)
    pdf.cell(90, 10, txt="Service Description", border=1)
    pdf.cell(90, 10, txt="Value (OMR)", border=1, ln=True)
    for service, value in invoice_data['services']:
        pdf.cell(90, 10, txt=service, border=1)
        pdf.cell(90, 10, txt=f"{value:.2f}", border=1, ln=True)
    
    # Add total and VAT
    total = sum(value for _, value in invoice_data['services'])
    vat = total * 0.05 if apply_vat else 0  # VAT applied if checkbox is checked
    grand_total = total + vat
    
    pdf.cell(90, 10, txt="Total", border=1)
    pdf.cell(90, 10, txt=f"{total:.2f}", border=1, ln=True)
    
    if apply_vat:
        pdf.cell(90, 10, txt="VAT (5%)", border=1)
        pdf.cell(90, 10, txt=f"{vat:.2f}", border=1, ln=True)
    
    pdf.cell(90, 10, txt="Grand Total", border=1)
    pdf.cell(90, 10, txt=f"{grand_total:.2f}", border=1, ln=True)

    paragraph = "We kindly request that you access the invoice at your earliest convenience through our secure online portal/E-mail/PDF. Your prompt attention to this matter is greatly appreciated, as it will ensure the continued smooth operation of our professional relationship. Should you have any inquiries or require assistance, please do not hesitate to contact us."
    
    pdf.set_xy(10, pdf.get_y() + 5)
    pdf.multi_cell(180, 8, txt=paragraph)  # Use 8 as the height for reduced line spacing

    # Add signing staff agent and stamp at the bottom
    y_position = pdf.get_y() + 30
    pdf.set_xy(10, y_position)
    
    if os.path.exists('stamp.jpg'):
        pdf.image('stamp.jpg', x=10, y=y_position - 25, w=40)  # Adjust the position and size as needed

    pdf.cell(200, 39, txt=f"Application Signed By: {invoice_data['signed_by']}", ln=True, align="L")
    
    # Save PDF
    pdf_output = f"invoice_{invoice_data['invoice_number']}.pdf"
    pdf.output(pdf_output)
    
    return pdf_output

def generate_invoice_number():
    today_str = datetime.now().strftime("%d%m%Y")
    daily_count = get_daily_invoice_count() + 1
    return f"{today_str}-{daily_count:04d}"

def clear_all_invoices():
    conn = sqlite3.connect('invoices.db')
    c = conn.cursor()
    c.execute('DELETE FROM invoices')
    conn.commit()
    conn.close()

# Streamlit app layout
st.title("Invoice Maker")

# Sidebar Initialization
with st.sidebar:
    st.image("logo.png")
    st.header(" Bill Generator App For Aiwa:tada:", divider='rainbow')
    with st.expander("Switch Organization"):
        st.write("""
        * Ahamad Al-Ajmi Garages
        * Aiwa Digitals
        """)
    with st.expander("App Usage Instructions"):
        st.write("""
        * Ahamad Al-Ajmi Garages
        * Aiwa Digitals
        """)
    st.header(" Invoice History", divider='rainbow')
    
    invoices = get_all_invoices()
    with st.expander("Last 10 Invoices:"):
        for invoice in invoices:
            st.write(f"Invoice Number: {invoice[1]}, Client: {invoice[2]}")
     
    if st.button("Clear All Invoices"):
        st.session_state.clear_confirm = True

    if st.session_state.clear_confirm:
        st.write("Are you sure you want to delete all invoices from the database and filesystem?")
        st.session_state.confPass = st.text_input("Enter Admin Password to clear data:", type="password")
         
        if st.session_state.confPass != "Bhogganddogg1!":
            st.warning('Please provide Printing Password.')
        else:
            st.success('Password Accepted')
            st.warning("Deleting all invoices...")
            clear_all_invoices()  # Call function to clear database
            st.success("All invoices deleted.")
            st.session_state.clear_confirm = False

# Stage 1: Client Information
if st.session_state.stage == 1:
    st.session_state.invoice_data['client_name'] = st.text_input("Client Name", "Company Name")
    st.session_state.invoice_data['client_address'] = st.text_area("Provide Billable Client Address", "Client Address")
    st.session_state.invoice_data['client_contact'] = st.text_input("Client Contact Number", "Company Contact")
    st.session_state.invoice_data['invoice_number'] = generate_invoice_number()
    st.write(f"Invoice Number: {st.session_state.invoice_data['invoice_number']}")
    submitted = st.button("Next")

    if submitted:
        st.session_state.stage = 2

# Stage 2: Aiwa Provided Services and Signing Agent
if st.session_state.stage == 2:
    num_services = st.number_input("Number of Services", min_value=1, step=1, value=1)

    services = []
    for i in range(num_services):
        service_name = st.text_input(f"Service {i+1} Description")
        service_value = st.number_input(f"Service {i+1} Value", min_value=0.0, step=0.01)
        services.append((service_name, service_value))
    
    signed_by = st.selectbox("Application Signed By", ["Imaaduddin Khan", "Bilawal Ali"])

    st.session_state.apply_vat = st.checkbox("Apply VAT (5%)", value=True)

    password = st.text_input("Enter Password to Print Invoice:", type="password")
    
    if password != "AiwaMediaAdmin":
        st.warning('Please provide Printing Password.')
        st.stop()   
    st.success('Password Accepted')

    submitted = st.button("Generate Invoice")

    if submitted:
        st.toast('Feeding the data')
        time.sleep(.5)
        st.toast('Generating PDF')
        time.sleep(.5)
        st.toast('Invoice Generated!', icon='🎉')
        invoice_data = {
          'client_name': st.session_state.invoice_data['client_name'],
          'client_address': st.session_state.invoice_data['client_address'],
          'client_contact': st.session_state.invoice_data['client_contact'],
          'invoice_number': st.session_state.invoice_data['invoice_number'],
          'services': services,
          'signed_by': signed_by
        }

        pdf_file = create_pdf(invoice_data, st.session_state.apply_vat)
        if pdf_file:
            save_invoice_data(invoice_data, pdf_file)
            st.success(f"Invoice generated: {pdf_file}")
            st.session_state.pdf_file = pdf_file

        # Reset stage for next use
        st.session_state.stage = 1

# Download button for the generated PDF
if st.session_state.pdf_file:
    with open(st.session_state.pdf_file, "rb") as file:
        st.download_button(label="Download Invoice", data=file, file_name=st.session_state.pdf_file, mime="application/pdf")
        st.session_state.pdf_file = None  # Reset after download
