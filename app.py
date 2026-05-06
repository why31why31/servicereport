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

# 2. DEFINISI KELAS PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SERVICE REPORT', 1, 1, 'C')
        self.ln(5)

# 3. FUNGSI PENYIMPANAN EXCEL
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
        st.error(f"⚠️ Tutup file '{EXCEL_FILE}' di Excel terlebih dahulu!")
        return False
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
        return False

# 4. FUNGSI PEMBUATAN PDF[cite: 1]
def create_pdf(data, sig_t=None, sig_c=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Informasi Utama[cite: 1]
    pdf.cell(100, 10, f"Customer: {data['Customer']}", border=1)
    pdf.cell(90, 10, f"Report No: {data['No']}", border=1, ln=1)
    pdf.cell(100, 10, f"Machine Type: {data['Machine Type']}", border=1)
    pdf.cell(90, 10, f"Date: {data['Date']}", border=1, ln=1)
    pdf.cell(100, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(90, 10, f"Completed By: {data['Completed By']}", border=1, ln=1)
    
    pdf.ln(5)
    
    # Masalah & Tindakan[cite: 1]
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Problem Description:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Problem'], border=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Report / Follow Up Action:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Follow Up'], border=1)
    
    pdf.ln(10)
    
    # Label Tanda Tangan[cite: 1]
    pdf.cell(90, 10, "Technician,", align='C')
    pdf.cell(90, 10, "Customer,", ln=1, align='C')
    
    sig_y = pdf.get_y()
    
    # Memasukkan Gambar Tanda Tangan (Mendukung Transparansi)[cite: 1]
    if sig_t:
        pdf.image(sig_t, x=40, y=sig_y, w=30)
    if sig_c:
        pdf.image(sig_c, x=140, y=sig_y, w=30)
    
    pdf.ln(25)
    
    # Nama Terang[cite: 1]
    pdf.cell(90, 10, f"( {data['Completed By']} )", align='C')
    pdf.cell(90, 10, f"( {data['Meet With']} )", ln=1, align='C')

    # Kembalikan dalam format bytes[cite: 1]
    return bytes(pdf.output())

# 5. ANTARMUKA STREAMLIT (UI)[cite: 1]
st.set_page_config(page_title="Service Report System", layout="centered")
st.title("Digital Service Report")
st.info("Input data servis untuk PT. Finpac Anugerah Indonesia.")[cite: 1]

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
    
    st.divider()
    
    # Area Tanda Tangan Digital dengan Background Transparan[cite: 1]
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(
            stroke_width=2, 
            stroke_color="#000", 
            background_color="rgba(0,0,0,0)", # Transparan[cite: 1]
            height=150, 
            width=300, 
            key="c_t"
        )
    with col_sig2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(
            stroke_width=2, 
            stroke_color="#000", 
            background_color="rgba(0,0,0,0)", # Transparan[cite: 1]
            height=150, 
            width=300, 
            key="c_c"
        )

    submitted = st.form_submit_button("Simpan Data & Buat Laporan")

# 6. LOGIKA SETELAH SUBMIT[cite: 1]
if submitted:
    if not report_no or not completed_by:
        st.warning("Nomor Report dan Nama Teknisi tidak boleh kosong!")
    else:
        # Konversi ke PIL Image dengan mode RGBA[cite: 1]
        img_t = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        img_c = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
            
        report_data = {
            "No": report_no, "Completed By": completed_by, "Date": str(report_date),
            "Customer": customer, "Meet With": meet_with, "Machine Type": machine_type,
            "Problem": problem, "Follow Up": follow_up
        }
        
        if save_to_excel(report_data):
            st.session_state['last_data'] = report_data
            st.session_state['sig_t'] = img_t
            st.session_state['sig_c'] = img_c
            st.success("Laporan berhasil disimpan!")

# 7. TOMBOL DOWNLOAD[cite: 1]
if 'last_data' in st.session_state:
    st.divider()
    try:
        pdf_file = create_pdf(
            st.session_state['last_data'], 
            st.session_state['sig_t'], 
            st.session_state['sig_c']
        )
        st.download_button(
            label="⬇️ Download PDF Service Report",
            data=pdf_file,
            file_name=f"Report_{st.session_state['last_data']['No']}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Gagal memproses PDF: {e}")
