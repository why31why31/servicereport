import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF
import os

# Set up the file path for saving data
EXCEL_FILE = "service_reports.xlsx"

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'SERVICE REPORT', 1, 1, 'C')
        self.ln(5)

def create_pdf(data):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Header Information Table
    pdf.cell(100, 10, f"Customer: {data['Customer']}", border=1)
    pdf.cell(90, 10, f"Report No: {data['No']}", border=1, ln=1)
    
    pdf.cell(100, 10, f"Machine Type: {data['Machine Type']}", border=1)
    pdf.cell(90, 10, f"Date: {data['Date']}", border=1, ln=1)
    
    pdf.cell(100, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(90, 10, f"Completed By: {data['Completed By']}", border=1, ln=1)
    
    pdf.ln(5)
    
    # Problem Section
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Problem:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Problem'], border=1)
    
    pdf.ln(5)
    
    # Follow Up Section
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Report / Follow Up:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Follow Up'], border=1)
    
    # FIX: Check if the output is already bytes, otherwise convert it
    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin-1')
    return bytes(output)
def save_to_excel(new_data):
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    else:
        df = pd.DataFrame([new_data])
    df.to_excel(EXCEL_FILE, index=False)

# --- Streamlit UI ---
st.title("Service Report Entry System")

# Start of the form
with st.form("main_service_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        report_no = st.text_input("Service Report No")
        completed_by = st.text_input("Completed By")
        report_date = st.date_input("Date", value=date.today())
        
    with col2:
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine_type = st.text_input("Machine Type")
        meet_with = st.text_input("Meet With")

    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")

    # This is the button that MUST be inside the 'with st.form' block
    submitted = st.form_submit_button("Save Report & Generate PDF")

# Processing after submission
if submitted:
    if not report_no:
        st.error("Please enter a Report Number.")
    else:
        report_data = {
            "No": report_no,
            "Completed By": completed_by,
            "Date": str(report_date),
            "Customer": customer,
            "Meet With": meet_with,
            "Machine Type": machine_type,
            "Problem": problem,
            "Follow Up": follow_up
        }
        
        # Save to Excel
        save_to_excel(report_data)
        st.session_state['last_report'] = report_data
        st.success(f"Report {report_no} saved to Excel!")

# Show download button if a report was just saved
if 'last_report' in st.session_state:
    st.info("Your report is ready for download.")
    try:
        pdf_bytes = create_pdf(st.session_state['last_report'])
        st.download_button(
            label="Download PDF Report",
            data=pdf_bytes,
            file_name=f"Service_Report_{st.session_state['last_report']['No']}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
