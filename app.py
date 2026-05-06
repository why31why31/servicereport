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
    def __init__(self, logo_img=None, logo_w=30):
        super().__init__()
        self.logo_img = logo_img
        self.logo_w = logo_w

    def header(self):
        if self.logo_img:
            # Memasukkan logo ke Kop Surat
            self.image(self.logo_img, x=10, y=8, w=self.logo_w)
            self.set_x(10 + self.logo_w + 5)
        
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SERVICE REPORT', 0, 1, 'R')
        self.ln(10)
        self.line(10, self.get_y(), 200, self.get_y())
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
        st.error(f"⚠️ Gagal menyimpan! Mohon tutup file '{EXCEL_FILE}' di Excel.")
        return False
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
        return False

# 4. FUNGSI PEMBUATAN PDF
def create_pdf(data, sig_t=None, sig_c=None, logo=None, logo_w=30):
    pdf = PDF(logo_img=logo, logo_w=logo_w)
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Informasi Utama
    pdf.cell(100, 10, f"Customer: {data['Customer']}", border=1)
    pdf.cell(90, 10, f"Report No: {data['No']}", border=1, ln=1)
    pdf.cell(100, 10, f"Machine Type: {data['Machine Type']}", border=1)
    pdf.cell(90, 10, f"Date: {data['Date']}", border=1, ln=1)
    pdf.cell(100, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(90, 10, f"Completed By: {data['Completed By']}", border=1, ln=1)
    
    pdf.ln(5)
    
    # Masalah & Tindakan
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
    
    # Label Tanda Tangan
    pdf.cell(90, 10, "Technician,", align='C')
    pdf.cell(90, 10, "Customer,", ln=1, align='C')
    
    sig_y = pdf.get_y()
    
    if sig_t:
        pdf.image(sig_t, x=40, y=sig_y, w=30)
    if sig_c:
        pdf.image(sig_c, x=140, y=sig_y, w=30)
    
    pdf.ln(25)
    
    # Nama Terang
    pdf.cell(90, 10, f"( {data['Completed By']} )", align='C')
    pdf.cell(90, 10, f"( {data['Meet With']} )", ln=1, align='C')

    return bytes(pdf.output())

# 5. ANTARMUKA STREAMLIT (UI)
st.set_page_config(page_title="Service Report System", layout="centered")
st.title("Digital Service Report")

# Sidebar untuk Logo
st.sidebar.header("Pengaturan Kop Surat")
uploaded_logo = st.sidebar.file_uploader("Upload Logo Perusahaan", type=["png", "jpg", "jpeg"])
logo_width = st.sidebar.slider("Ukuran Lebar Logo (mm)", 10, 100, 30)

st.info("Input data servis untuk PT. Finpac Anugerah Indonesia.")

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
    
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(
            stroke_width=2, 
            stroke_color="#000", 
            background_color="rgba(0,0,0,0)", 
            height=150, 
            width=300, 
            key="c_t"
        )
    with col_sig2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(
            stroke_width=2, 
            stroke_color="#000", 
            background_color="rgba(0,0,0,0)", 
            height=150, 
            width=300, 
            key="c_c"
        )

    submitted = st.form_submit_button("Simpan Data & Buat Laporan")

# 6. LOGIKA SETELAH SUBMIT
if submitted:
    if not report_no or not completed_by:
        st.warning("Nomor Report dan Nama Teknisi tidak boleh kosong!")
    else:
        final_logo = Image.open(uploaded_logo) if uploaded_logo else None
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
            st.session_state['logo'] = final_logo
            st.session_state['logo_w'] = logo_width
            st.success("Laporan berhasil disimpan!")

# 7. TOMBOL DOWNLOAD
if 'last_data' in st.session_state:
    st.divider()
    try:
        pdf_file = create_pdf(
            st.session_state['last_data'], 
            st.session_state['sig_t'], 
            st.session_state['sig_c'],
            logo=st.session_state.get('logo'),
            logo_w=st.session_state.get('logo_w', 30)
        )
        st.download_button(
            label="⬇️ Download PDF Service Report",
            data=pdf_file,
            file_name=f"Report_{st.session_state['last_data']['No']}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Gagal memproses PDF: {e}")
