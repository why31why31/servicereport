import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF
import os

# Konfigurasi nama file
EXCEL_FILE = "service_reports.xlsx"

# --- Kelas PDF untuk Layout Laporan ---
class PDF(FPDF):
    def header(self):
        # Header Laporan
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SERVICE REPORT', 1, 1, 'C')
        self.ln(5)

def create_pdf(data):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Informasi Header
    pdf.cell(100, 10, f"Customer: {data['Customer']}", border=1)
    pdf.cell(90, 10, f"Report No: {data['No']}", border=1, ln=1)
    
    pdf.cell(100, 10, f"Machine Type: {data['Machine Type']}", border=1)
    pdf.cell(90, 10, f"Date: {data['Date']}", border=1, ln=1)
    
    pdf.cell(100, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(90, 10, f"Completed By: {data['Completed By']}", border=1, ln=1)
    
    pdf.ln(5)
    
    # Bagian Problem
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Problem:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Problem'], border=1)
    
    pdf.ln(5)
    
    # Bagian Follow Up
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Report / Follow Up:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Follow Up'], border=1)
    
    pdf.ln(25) # Ruang untuk tanda tangan

    # --- Kolom Tanda Tangan ---
    current_y = pdf.get_y()
    
    # Kolom Kiri (Teknisi)
    pdf.set_xy(10, current_y)
    pdf.cell(90, 10, "Technician,", ln=0, align='C')
    
    # Kolom Kanan (Customer)
    pdf.set_xy(110, current_y)
    pdf.cell(90, 10, "Customer,", ln=1, align='C')
    
    pdf.ln(20) # Ruang tanda tangan basah
    
    # Nama Terang
    final_y = pdf.get_y()
    pdf.set_xy(10, final_y)
    pdf.cell(90, 10, f"( {data['Completed By']} )", ln=0, align='C')
    
    pdf.set_xy(110, final_y)
    pdf.cell(90, 10, f"( {data['Meet With']} )", ln=1, align='C')

    # Konversi ke bytes untuk download Streamlit
    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin-1')
    return bytes(output)

# --- Fungsi Penyimpanan Data ---
def save_to_excel(new_data):
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
        
        df.to_excel(EXCEL_FILE, index=False)
        return True
    except PermissionError:
        st.error(f"⚠️ Gagal menyimpan! Tutup file '{EXCEL_FILE}' di Excel terlebih dahulu.")
        return False
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
        return False

# --- Tampilan Utama Streamlit ---
st.set_page_config(page_title="Service Report System", layout="centered")
st.title("Input Service Report")

with st.form("form_laporan"):
    col1, col2 = st.columns(2)
    
    with col1:
        report_no = st.text_input("Service Report No")
        completed_by = st.text_input("Completed By (Teknisi)")
        report_date = st.date_input("Date", value=date.today())
        
    with col2:
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine_type = st.text_input("Machine Type (Kilian/Romaco)")
        meet_with = st.text_input("Meet With (PIC Customer)")

    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")

    # Tombol submit harus berada di dalam blok 'with st.form'
    submitted = st.form_submit_button("Simpan Data & Buat PDF")

# Proses setelah tombol diklik
if submitted:
    if not report_no or not completed_by:
        st.warning("Mohon isi nomor laporan dan nama teknisi.")
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
        
        if save_to_excel(report_data):
            st.session_state['last_report'] = report_data
            st.success(f"Data Berhasil Disimpan ke {EXCEL_FILE}!")

# Bagian Download PDF
if 'last_report' in st.session_state:
    st.divider()
    st.subheader("Opsi Unduhan")
    try:
        pdf_bytes = create_pdf(st.session_state['last_report'])
        st.download_button(
            label="⬇️ Download Report (PDF)",
            data=pdf_bytes,
            file_name=f"Report_{st.session_state['last_report']['No']}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Gagal membuat PDF: {e}")
