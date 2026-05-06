import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# 1. KONFIGURASI FILE
EXCEL_FILE = "service_reports.xlsx"

# 2. DEFINISI KELAS & FUNGSI (Harus di atas agar terbaca)
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SERVICE REPORT', 1, 1, 'C')
        self.ln(5)

def save_to_excel(new_data):
    """Fungsi ini harus didefinisikan sebelum dipanggil di baris 145"""
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
        df.to_excel(EXCEL_FILE, index=False)
        return True
    except PermissionError:
        st.error(f"⚠️ Tutup file '{EXCEL_FILE}' di Excel!")
        return False
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
        return False

def create_pdf(data, sig_tech=None, sig_cust=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Data
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
    current_y = pdf.get_y()

    # Tanda Tangan[cite: 1]
    pdf.cell(90, 10, "Technician,", ln=0, align='C')
    pdf.cell(90, 10, "Customer,", ln=1, align='C')
    
    if sig_tech:
        buf_t = io.BytesIO()
        sig_tech.save(buf_t, format='PNG')
        buf_t.seek(0)
        pdf.image(buf_t, x=35, y=pdf.get_y(), w=30, type='PNG')
        
    if sig_cust:
        buf_c = io.BytesIO()
        sig_cust.save(buf_c, format='PNG')
        buf_c.seek(0)
        pdf.image(buf_c, x=135, y=pdf.get_y(), w=30, type='PNG')
    
    pdf.ln(25)
    pdf.cell(90, 10, f"( {data['Completed By']} )", ln=0, align='C')
    pdf.cell(90, 10, f"( {data['Meet With']} )", ln=1, align='C')

    output = pdf.output(dest='S')
    return bytes(output) if not isinstance(output, str) else output.encode('latin-1')

# 3. LOGIKA UTAMA (UI)[cite: 1]
st.set_page_config(page_title="Service Report System", layout="centered")
st.title("Service Report Digital Signature")

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
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.write("Tanda Tangan Teknisi:")
        canvas_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, key="c1")
    with col_sig2:
        st.write("Tanda Tangan Customer:")
        canvas_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, key="c2")

    submitted = st.form_submit_button("Simpan & Proses Laporan")

if submitted:
    if not report_no or not completed_by:
        st.error("Isi Nomor Report dan Nama Teknisi!")
    else:
        # Proses Gambar Tanda Tangan[cite: 1]
        sig_t = Image.fromarray(canvas_tech.image_data.astype('uint8'), 'RGBA') if canvas_tech.image_data is not None else None
        sig_c = Image.fromarray(canvas_cust.image_data.astype('uint8'), 'RGBA') if canvas_cust.image_data is not None else None
            
        report_data = {
            "No": report_no, "Completed By": completed_by, "Date": str(report_date),
            "Customer": customer, "Meet With": meet_with, "Machine Type": machine_type,
            "Problem": problem, "Follow Up": follow_up
        }
        
        # Pemanggilan fungsi save_to_excel sekarang aman karena sudah didefinisikan di atas[cite: 1]
        if save_to_excel(report_data):
            st.session_state['last_report'] = report_data
            st.session_state['sig_t'] = sig_t
            st.session_state['sig_c'] = sig_c
            st.success("Data Berhasil Disimpan!")

if 'last_report' in st.session_state:
    st.divider()
    pdf_bytes = create_pdf(st.session_state['last_report'], st.session_state['sig_t'], st.session_state['sig_c'])
    st.download_button(label="⬇️ Download PDF", data=pdf_bytes, file_name=f"Report_{st.session_state['last_report']['No']}.pdf", mime="application/pdf")
