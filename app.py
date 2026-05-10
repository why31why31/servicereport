import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# 1. KONFIGURASI FILE
EXCEL_FILE = "service_reports.xlsx"

# 2. DEFINISI KELAS PDF
class PDF(FPDF):
    def __init__(self, logo_img=None, logo_w=30):
        super().__init__()
        self.logo_img = logo_img
        self.logo_w = logo_w

    def header(self):
        if self.page_no() == 1:
            if self.logo_img:
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
    except Exception as e:
        st.error(f"Error Excel: {e}")
        return False

# 4. FUNGSI PEMBUATAN PDF
def create_pdf(data, sig_t=None, sig_c=None, logo=None, logo_w=30, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Informasi Utama
    pdf.cell(95, 10, f"Completed By: {data['Completed By']}", border=1)
    pdf.cell(95, 10, f"Customer: {data['Customer']}", border=1, ln=1)
    pdf.cell(95, 10, f"Machine: {data['Machine']}", border=1)
    pdf.cell(95, 10, f"Date: {data['Date']}", border=1, ln=1)
    pdf.cell(95, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(47.5, 10, f"Type: {data['Type']}", border=1)
    pdf.cell(47.5, 10, f"Serial No: {data['Serial No']}", border=1, ln=1)
    
    pdf.ln(5)
    
    # Masalah
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "Problem Description:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, data['Problem'], border=1)
    
    pdf.ln(5)

    # Follow Up Action
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "Report / Follow Up Action:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, data['Follow Up'], border=1)

    # --- LOGIKA LAMPIRAN GAMBAR (SATU FRAME DI BAWAH FOLLOW UP) ---
    if extra_items:
        valid_items = [item for item in extra_items if item['file']]
        for i, item in enumerate(valid_items):
            # Cek sisa ruang halaman sebelum gambar
            if pdf.get_y() > 230:
                pdf.add_page()
            
            pdf.ln(2)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 6, f"Attachment {i+1}:", ln=1)
            
            # Hitung tinggi proporsional
            w_orig, h_orig = item['file'].size
            img_w = 120 # Ukuran diperbesar karena tidak berdampingan
            img_h = (h_orig / w_orig) * img_w
            
            # Masukkan Gambar
            pdf.image(item['file'], x=pdf.get_x() + 5, y=pdf.get_y(), w=img_w)
            
            # Keterangan
            pdf.set_y(pdf.get_y() + img_h + 2)
            pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(img_w, 4, f"Ket: {item['caption']}")
            pdf.ln(2)

    # Tanda Tangan
    if pdf.get_y() > 240:
        pdf.add_page()
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 10, "Technician,", align='C')
    pdf.cell(95, 10, "Customer,", ln=1, align='C')
    
    sig_y = pdf.get_y()
    if sig_t: pdf.image(sig_t, x=42, y=sig_y, w=25)
    if sig_c: pdf.image(sig_c, x=138, y=sig_y, w=25)
    
    pdf.ln(25)
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 10, f"( {data['Completed By']} )", align='C')
    pdf.cell(95, 10, f"( {data['Meet With']} )", ln=1, align='C')

    return bytes(pdf.output())

# 5. ANTARMUKA STREAMLIT
st.set_page_config(page_title="Service Report System", layout="centered")
st.title("Digital Service Report")

# Sidebar
st.sidebar.header("Kop & Dokumentasi")
uploaded_logo = st.sidebar.file_uploader("Logo Kop", type=["png", "jpg", "jpeg"])
logo_w = st.sidebar.slider("Lebar Logo (mm)", 10, 100, 30)
st.sidebar.divider()
st.sidebar.subheader("Foto Dokumentasi")
img1 = st.sidebar.file_uploader("Foto 1", type=["png", "jpg", "jpeg"], key="u1")
cap1 = st.sidebar.text_input("Ket Foto 1", key="t1")
img2 = st.sidebar.file_uploader("Foto 2", type=["png", "jpg", "jpeg"], key="u2")
cap2 = st.sidebar.text_input("Ket Foto 2", key="t2")

# FORM INPUT
with st.form("main_form"):
    c1, c2 = st.columns(2)
    with c1:
        completed_by = st.text_input("Completed By")
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine = st.text_input("Machine")
    with c2:
        report_date = st.date_input("Date", value=date.today())
        meet_with = st.text_input("Meet With")
        sc1, sc2 = st.columns(2)
        with sc1: m_type = st.text_input("Type")
        with sc2: serial_no = st.text_input("Serial No")

    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")
    
    st.divider()
    cs1, cs2 = st.columns(2)
    with cs1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=120, width=250, key="c_t")
    with cs2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=120, width=250, key="c_c")

    submitted = st.form_submit_button("Simpan & Lihat Preview")

# 6. LOGIKA PREVIEW & DOWNLOAD
if submitted:
    if not completed_by:
        st.error("Nama Teknisi harus diisi!")
    else:
        # Konversi data
        logo_img = Image.open(uploaded_logo) if uploaded_logo else None
        e_items = [
            {'file': Image.open(img1) if img1 else None, 'caption': cap1},
            {'file': Image.open(img2) if img2 else None, 'caption': cap2}
        ]
        img_t = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        img_c = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
        
        report_data = {
            "Completed By": completed_by, "Customer": customer, "Machine": machine,
            "Date": str(report_date), "Meet With": meet_with, "Type": m_type,
            "Serial No": serial_no, "Problem": problem, "Follow Up": follow_up
        }
        
        if save_to_excel(report_data):
            st.session_state.update({
                'last_data': report_data, 'sig_t': img_t, 'sig_c': img_c, 
                'logo': logo_img, 'logo_w': logo_w, 'extra_items': e_items
            })
            st.success("Data tersimpan!")

# LIVE PREVIEW PDF
if 'last_data' in st.session_state:
    st.write("---")
    st.subheader("🔍 PDF Live Preview")
    
    pdf_bytes = create_pdf(
        st.session_state['last_data'], 
        st.session_state['sig_t'], 
        st.session_state['sig_c'], 
        logo=st.session_state.get('logo'), 
        logo_w=st.session_state.get('logo_w', 30), 
        extra_items=st.session_state.get('extra_items')
    )

    # Encode PDF ke base64
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    
    st.markdown(pdf_display, unsafe_allow_html=True)
    
    st.download_button(
        label="⬇️ Download PDF Sekarang",
        data=pdf_bytes,
        file_name=f"Report_{st.session_state['last_data']['Serial No']}.pdf",
        mime="application/pdf"
    )
