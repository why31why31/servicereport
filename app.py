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
        st.error(f"⚠️ Gagal! Tutup file '{EXCEL_FILE}' di Excel.")
        return False
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# 4. FUNGSI PEMBUATAN PDF
def create_pdf(data, sig_t=None, sig_c=None, logo=None, logo_w=30, extra_items=None):
    pdf = PDF(logo_img=logo, logo_w=logo_w)
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Informasi Utama (Serial No sudah pindah ke sebelah Type)
    pdf.cell(95, 10, f"Completed By: {data['Completed By']}", border=1)
    pdf.cell(95, 10, f"Customer: {data['Customer']}", border=1, ln=1)
    
    pdf.cell(95, 10, f"Machine: {data['Machine']}", border=1)
    pdf.cell(95, 10, f"Date: {data['Date']}", border=1, ln=1)
    
    pdf.cell(95, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(47.5, 10, f"Type: {data['Type']}", border=1)
    pdf.cell(47.5, 10, f"Serial No: {data['Serial No']}", border=1, ln=1)
    
    pdf.cell(190, 10, f"Service Report No: {data['No']}", border=1, ln=1)
    
    pdf.ln(5)
    
    # Deskripsi Masalah & Tindakan
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Problem Description:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Problem'], border=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Report / Follow Up Action:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Follow Up'], border=1)
    
    # Logika Gambar Berdampingan
    if extra_items:
        pdf.ln(5)
        valid_items = [item for item in extra_items if item['file']]
        x_start, current_x, max_row_height = 15, 15, 0
        
        for item in valid_items:
            if current_x + item['width'] > 195:
                pdf.set_y(pdf.get_y() + max_row_height + 10)
                current_x, max_row_height = x_start, 0
            if pdf.get_y() > 220:
                pdf.add_page()
                current_x = x_start
            
            img_y = pdf.get_y()
            pdf.image(item['file'], x=current_x, y=img_y, w=item['width'])
            pdf.set_xy(current_x, img_y + (item['width'] / 1.5) + 2)
            pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(item['width'], 4, f"Ket: {item['caption']}", align='L')
            
            current_x += item['width'] + 10
            row_h = (item['width'] / 1.5) + 15
            if row_h > max_row_height: max_row_height = row_h
        
        pdf.set_y(pdf.get_y() + max_row_height)

    pdf.ln(10)
    
    # Tanda Tangan
    if pdf.get_y() > 240: pdf.add_page()
    pdf.cell(95, 10, "Technician,", align='C')
    pdf.cell(95, 10, "Customer,", ln=1, align='C')
    
    sig_y = pdf.get_y()
    if sig_t: pdf.image(sig_t, x=42, y=sig_y, w=30)
    if sig_c: pdf.image(sig_c, x=138, y=sig_y, w=30)
    
    pdf.ln(25)
    pdf.cell(95, 10, f"( {data['Completed By']} )", align='C')
    pdf.cell(95, 10, f"( {data['Meet With']} )", ln=1, align='C')

    return bytes(pdf.output())

# 5. ANTARMUKA STREAMLIT
st.set_page_config(page_title="Service Report System", layout="centered")
st.title("Digital Service Report")

# Sidebar Pengaturan
st.sidebar.header("Kop & Dokumentasi")
uploaded_logo = st.sidebar.file_uploader("Logo Kop Surat", type=["png", "jpg", "jpeg"])
logo_w = st.sidebar.slider("Lebar Logo (mm)", 10, 100, 30)

st.sidebar.divider()
st.sidebar.subheader("Foto Dokumentasi")
img1 = st.sidebar.file_uploader("Foto 1", type=["png", "jpg", "jpeg"], key="f1")
cap1 = st.sidebar.text_input("Keterangan Foto 1", key="c1")
w1 = st.sidebar.slider("Lebar Foto 1 (mm)", 20, 180, 80, key="w1")

img2 = st.sidebar.file_uploader("Foto 2", type=["png", "jpg", "jpeg"], key="f2")
cap2 = st.sidebar.text_input("Keterangan Foto 2", key="c2")
w2 = st.sidebar.slider("Lebar Foto 2 (mm)", 20, 180, 80, key="w2")

# Formulir Utama (Urutan Input Sesuai Permintaan)
with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        completed_by = st.text_input("Completed By (Teknisi)")
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine = st.text_input("Machine (e.g. Kilian)")
    with col2:
        report_date = st.date_input("Date", value=date.today())
        meet_with = st.text_input("Meet With (PIC)")
        # Type dan Serial No dalam satu baris
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            m_type = st.text_input("Type")
        with sub_col2:
            serial_no = st.text_input("Serial No")

    report_no = st.text_input("Service Report No")
    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")
    
    st.divider()
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=150, width=300, key="c_t")
    with col_sig2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=150, width=300, key="c_c")

    submitted = st.form_submit_button("Simpan & Proses PDF")

# 6. LOGIKA SUBMIT
if submitted:
    if not completed_by or not customer:
        st.error("Mohon lengkapi data Teknisi dan Customer!")
    else:
        logo_img = Image.open(uploaded_logo) if uploaded_logo else None
        extra_items = [
            {'file': Image.open(img1) if img1 else None, 'caption': cap1, 'width': w1},
            {'file': Image.open(img2) if img2 else None, 'caption': cap2, 'width': w2}
        ]
        img_t = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        img_c = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
            
        report_data = {
            "Completed By": completed_by, "Customer": customer, "Machine": machine,
            "Date": str(report_date), "Meet With": meet_with, "Type": m_type,
            "Serial No": serial_no, "No": report_no, "Problem": problem, "Follow Up": follow_up
        }
        
        if save_to_excel(report_data):
            st.session_state.update({
                'last_data': report_data, 'sig_t': img_t, 'sig_c': img_c,
                'logo': logo_img, 'logo_w': logo_w, 'extra_items': extra_items
            })
            st.success("Laporan Berhasil Disimpan!")

# 7. DOWNLOAD PDF
if 'last_data' in st.session_state:
    st.divider()
    try:
        pdf_file = create_pdf(
            st.session_state['last_data'], 
            st.session_state['sig_t'], 
            st.session_state['sig_c'],
            logo=st.session_state.get('logo'),
            logo_w=st.session_state.get('logo_w', 30),
            extra_items=st.session_state.get('extra_items')
        )
        st.download_button(label="⬇️ Download PDF", data=pdf_file, file_name=f"Report_{st.session_state['last_data']['Serial No']}.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"Gagal memproses PDF: {e}")
