import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# Konfigurasi file
EXCEL_FILE = "service_reports.xlsx"

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SERVICE REPORT', 1, 1, 'C')
        self.ln(5)

def create_pdf(data, sig_tech=None, sig_cust=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Data Table (Tetap sama)
    pdf.cell(100, 10, f"Customer: {data['Customer']}", border=1)
    pdf.cell(90, 10, f"Report No: {data['No']}", border=1, ln=1)
    pdf.cell(100, 10, f"Machine Type: {data['Machine Type']}", border=1)
    pdf.cell(90, 10, f"Date: {data['Date']}", border=1, ln=1)
    pdf.cell(100, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(90, 10, f"Completed By: {data['Completed By']}", border=1, ln=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Problem:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Problem'], border=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Report / Follow Up:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Follow Up'], border=1)
    
    pdf.ln(10)

    # Label Tanda Tangan
    pdf.cell(90, 10, "Technician,", ln=0, align='C')
    pdf.cell(90, 10, "Customer,", ln=1, align='C')
    
    # --- PERBAIKAN PROSES TANDA TANGAN ---
    current_y = pdf.get_y()

    if sig_tech:
        buf_tech = io.BytesIO()
        sig_tech.save(buf_tech, format='PNG')
        buf_tech.seek(0)
        # Menambahkan parameter 'type' agar fpdf tidak mencari ekstensi file
        pdf.image(buf_tech, x=35, y=current_y, w=30, type='PNG')
        
    if sig_cust:
        buf_cust = io.BytesIO()
        sig_cust.save(buf_cust, format='PNG')
        buf_cust.seek(0)
        # Menambahkan parameter 'type' agar fpdf tidak mencari ekstensi file
        pdf.image(buf_cust, x=135, y=current_y, w=30, type='PNG')
    
    pdf.ln(25) 
    
    # Nama Terang
    pdf.cell(90, 10, f"( {data['Completed By']} )", ln=0, align='C')
    pdf.cell(90, 10, f"( {data['Meet With']} )", ln=1, align='C')

    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin-1')
    return bytes(output)

# --- UI Streamlit ---
st.set_page_config(page_title="Service Report Digital Sign", layout="centered")
st.title("Service Report & Digital Signature")

with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        report_no = st.text_input("Service Report No")
        completed_by = st.text_input("Completed By (Teknisi)")
        report_date = st.date_input("Date", value=date.today())
    with col2:
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine_type = st.text_input("Machine Type")
        meet_with = st.text_input("Meet With (PIC)")

    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")
    
    st.write("---")
    # Area Tanda Tangan
    col_sig1, col_sig2 = st.columns(2)
    
    with col_sig1:
        st.write("Tanda Tangan Teknisi:")
        canvas_tech = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#eeeeee",
            height=150,
            width=300,
            key="canvas_tech",
        )
        
    with col_sig2:
        st.write("Tanda Tangan Customer:")
        canvas_cust = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#eeeeee",
            height=150,
            width=300,
            key="canvas_cust",
        )

    submitted = st.form_submit_button("Simpan & Proses Laporan")

if submitted:
    if not report_no or not completed_by:
        st.error("Isi Nomor Report dan Nama Teknisi!")
    else:
        # Proses Gambar Tanda Tangan
        sig_tech_img = None
        sig_cust_img = None
        
        if canvas_tech.image_data is not None:
            sig_tech_img = Image.fromarray(canvas_tech.image_data.astype('uint8'), 'RGBA')
        if canvas_cust.image_data is not None:
            sig_cust_img = Image.fromarray(canvas_cust.image_data.astype('uint8'), 'RGBA')
            
        report_data = {
            "No": report_no, "Completed By": completed_by, "Date": str(report_date),
            "Customer": customer, "Meet With": meet_with, "Machine Type": machine_type,
            "Problem": problem, "Follow Up": follow_up
        }
        
        if save_to_excel(report_data):
            st.session_state['last_report'] = report_data
            st.session_state['sig_tech'] = sig_tech_img
            st.session_state['sig_cust'] = sig_cust_img
            st.success("Data dan Tanda Tangan Berhasil Diproses!")

if 'last_report' in st.session_state:
    st.divider()
    # Buat PDF dengan gambar tanda tangan
    pdf_bytes = create_pdf(
        st.session_state['last_report'], 
        st.session_state['sig_tech'], 
        st.session_state['sig_cust']
    )
    
    st.download_button(
        label="⬇️ Download PDF dengan Tanda Tangan",
        data=pdf_bytes,
        file_name=f"Report_{st.session_state['last_report']['No']}.pdf",
        mime="application/pdf"
    )
