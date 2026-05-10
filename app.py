import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- KONFIGURASI FILE ---
EXCEL_FILE = "service_reports.xlsx"

class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img

    def header(self):
        if self.page_no() == 1:
            if self.logo_img:
                # Pastikan logo proporsional
                self.image(self.logo_img, x=10, y=8, w=30)
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'SERVICE REPORT', 0, 1, 'R')
            self.ln(10)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)

# --- FUNGSI OPTIMASI GAMBAR (AUTO RESIZE) ---
def optimize_image(uploaded_file, max_size=(1000, 1000)):
    if uploaded_file is None:
        return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size, Image.LANCZOS)
    return img

# --- FUNGSI SIMPAN EXCEL ---
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
        st.error(f"Gagal akses Excel: {e}")
        return False

# --- FUNGSI BUAT PDF ---
def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None, img_width_adj=100):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Informasi
    pdf.cell(95, 10, f"Completed By: {data['Completed By']}", border=1)
    pdf.cell(95, 10, f"Customer: {data['Customer']}", border=1, ln=1)
    pdf.cell(95, 10, f"Machine: {data['Machine']}", border=1)
    pdf.cell(95, 10, f"Date: {data['Date']}", border=1, ln=1)
    pdf.cell(95, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(47.5, 10, f"Type: {data['Type']}", border=1)
    pdf.cell(47.5, 10, f"Serial No: {data['Serial No']}", border=1, ln=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "Problem Description:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, data['Problem'], border=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "Report / Follow Up Action:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, data['Follow Up'], border=1)

    # Lampiran Foto
    if extra_items:
        pdf.ln(5)
        for i, item in enumerate(extra_items):
            w_orig, h_orig = item.size
            img_w = img_width_adj 
            img_h = (h_orig / w_orig) * img_w
            
            if pdf.get_y() + img_h > 250:
                pdf.add_page()
            
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 7, f"Attachment {i+1}:", ln=1)
            
            x_pos = (210 - img_w) / 2
            pdf.image(item, x=x_pos, y=pdf.get_y(), w=img_w)
            pdf.set_y(pdf.get_y() + img_h + 8) 

    # Tanda Tangan
    if pdf.get_y() > 240: pdf.add_page()
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 10, "Technician,", align='C')
    pdf.cell(95, 10, "Customer,", ln=1, align='C')
    
    sig_y = pdf.get_y()
    if sig_t: pdf.image(sig_t, x=42, y=sig_y, w=25)
    if sig_c: pdf.image(sig_c, x=138, y=sig_y, w=25)
    
    pdf.ln(25)
    pdf.cell(95, 10, f"( {data['Completed By']} )", align='C')
    pdf.cell(95, 10, f"( {data['Meet With']} )", ln=1, align='C')

    return bytes(pdf.output())

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Finpac Service Report", layout="centered")
st.title("Digital Service Report")

# Sidebar
st.sidebar.header("Media & Settings")
uploaded_logo = st.sidebar.file_uploader("Upload Logo Perusahaan", type=["png", "jpg", "jpeg"])
st.sidebar.divider()
st.sidebar.subheader("Foto Lampiran")
uploaded_photos = st.sidebar.file_uploader("Pilih Foto Dokumentasi", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
img_adj = st.sidebar.slider("Lebar Foto di PDF (mm)", 30, 180, 100)

with st.form("main_form"):
    c1, c2 = st.columns(2)
    with c1:
        completed_by = st.text_input("Completed By (Teknisi)")
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine = st.text_input("Machine Name")
    with c2:
        report_date = st.date_input("Date", value=date.today())
        meet_with = st.text_input("Meet With (PIC)")
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

if submitted:
    if not completed_by: st.error("Isi Nama Teknisi!")
    else:
        logo_img = optimize_image(uploaded_logo, (400, 400))
        list_photos = [optimize_image(p, (1000, 1000)) for p in uploaded_photos] if uploaded_photos else []
        
        # Proses Tanda Tangan
        sig_t_img = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        sig_c_img = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
        
        report_data = {
            "Completed By": completed_by, "Customer": customer, "Machine": machine,
            "Date": str(report_date), "Meet With": meet_with, "Type": m_type,
            "Serial No": serial_no, "Problem": problem, "Follow Up": follow_up
        }
        
        if save_to_excel(report_data):
            st.session_state.update({
                'last_data': report_data, 'sig_t': sig_t_img, 'sig_c': sig_c_img, 
                'logo': logo_img, 'extra_items': list_photos, 'img_adj': img_adj
            })
            st.success("Data Berhasil Disimpan!")

# TAMPILAN PREVIEW PDF
if 'last_data' in st.session_state:
    st.write("---")
    st.subheader("🔍 PDF Live Preview")
    
    pdf_bytes = create_pdf(
        st.session_state['last_data'], 
        st.session_state['sig_t'], 
        st.session_state['sig_c'], 
        logo=st.session_state.get('logo'), 
        extra_items=st.session_state.get('extra_items'),
        img_width_adj=st.session_state.get('img_adj', 100)
    )

    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=f"Report_{st.session_state['last_data']['Serial No']}.pdf", mime="application/pdf")
