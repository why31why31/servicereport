import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONNECTION SETUP ---
SHEET_NAME = "Service Report Log" 

def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            return gspread.authorize(creds)
    except:
        return None

# --- 2. PDF ENGINE ---
class PDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path
        self.set_margin(15)

    def header(self):
        if self.page_no() == 1:
            if self.logo_path and os.path.exists(self.logo_path):
                # KOP DIBUAT LEBIH BESAR (w=70)
                self.image(self.logo_path, x=70, y=10, w=70)
                self.ln(35) # Memberi ruang setelah logo
            else:
                self.ln(10)
            
            self.set_fill_color(41, 128, 185)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(5)

def create_pdf(data, s_t, s_c, logo_path, photos):
    pdf = PDF(logo_path=logo_path)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    
    # Data Grid
    pdf.set_font("helvetica", 'B', 9)
    pdf.set_fill_color(245, 245, 245)
    
    # Baris data teknis
    fields = [
        [("Technician", data['cb']), ("Date", data['rd'])],
        [("Customer", data['cu']), ("Contact", data['mw'])],
        [("Machine", data['ma']), ("Type", data['ty']), ("SN", data['sn'])]
    ]

    for row in fields:
        for label, value in row:
            pdf.set_font("helvetica", 'B', 9)
            pdf.cell(25, 8, f" {label}:", fill=True)
            pdf.set_font("helvetica", '', 9)
            pdf.cell(65 if len(row)==2 else 35, 8, f" {value}", border='B')
        pdf.ln(10)
    
    pdf.ln(2)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['pr'])
    
    pdf.ln(4)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['fu'])

    # Photos Section (FIXED SEJAJAR KIRI KANAN)
    if photos:
        if pdf.get_y() > 180: pdf.add_page()
        pdf.ln(10)
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 8, "ATTACHMENTS / DOCUMENTATION", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        
        img_w, img_h = 85, 60
        y_anchor = pdf.get_y() # Mengunci posisi Y untuk baris foto yang sama

        for i, p in enumerate(photos):
            col = i % 2
            # Pindah halaman jika ruang tidak cukup untuk baris baru
            if col == 0 and (y_anchor + img_h + 15) > 275:
                pdf.add_page()
                y_anchor = pdf.get_y() + 5

            x_pos = 15 if col == 0 else 110
            
            # Gambar & Bingkai
            pdf.rect(x_pos, y_anchor, img_w, img_h)
            pdf.image(p['img'], x=x_pos+1, y=y_anchor+1, w=img_w-2, h=img_h-10)
            
            # Caption
            pdf.set_xy(x_pos, y_anchor + img_h - 7)
            pdf.set_font("helvetica", 'I', 8)
            pdf.cell(img_w, 5, f"Photo {i+1}: {p['cap']}", align='C')
            
            # Jika sudah foto kedua dalam satu baris, update posisi Y untuk baris berikutnya
            if col == 1 or i == len(photos)-1:
                y_anchor += (img_h + 10)
                pdf.set_y(y_anchor)

    # --- SIGNATURES LOCK DI PALING BAWAH HALAMAN ---
    # Jika sisa halaman terlalu sedikit, pindah halaman dulu
    if pdf.get_y() > 220:
        pdf.add_page()
    
    # Set posisi 60mm dari dasar kertas
    pdf.set_y(-60)
    sig_start_y = pdf.get_y()
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(90, 7, "Service Technician,", align='C')
    pdf.cell(90, 7, "Customer,", align='C')
    
    # Tanda Tangan (Posisi absolut di atas nama)
    if s_t: pdf.image(s_t, x=45, y=sig_start_y + 8, w=30)
    if s_c: pdf.image(s_c, x=135, y=sig_start_y + 8, w=30)
    
    # Nama (Terkunci di bawah area tanda tangan)
    pdf.set_y(sig_start_y + 35)
    pdf.set_font("helvetica", 'BU', 10)
    pdf.cell(90, 7, data['cb'], align='C')
    pdf.cell(90, 7, data['mw'], align='C')
    
    return bytes(pdf.output())

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Service Report", layout="centered")
st.markdown("<style>iframe{border:1px solid #ddd !important; border-radius:10px; background-color:white;}</style>", unsafe_allow_html=True)

st.title("Digital Service Report")
client = get_gspread_client()

with st.sidebar:
    st.header("Attachments")
    photo_files = st.file_uploader("Upload Photos", type=["jpg", "png"], accept_multiple_files=True)
    caps = [st.text_input(f"Caption {i+1}", key=f"c_{i}") for i in range(len(photo_files))]

col1, col2 = st.columns(2)
with col1:
    cb = st.text_input("Technician Name")
    cu = st.text_input("Customer Name", value="PT. Finpac Anugerah Indonesia")
    mw = st.text_input("Meet With")
with col2:
    rd = st.date_input("Date", value=date.today())
    ma = st.text_input("Machine")
    sn = st.text_input("Serial No")
ty = st.text_input("Machine Type")

pr = st.text_area("Problem Description")
fu = st.text_area("Action Taken / Follow Up")

st.write("---")
st.write("### Signatures")
# Lebar canvas tanda tangan disesuaikan agar nyaman di HP
can_t = st_canvas(stroke_width=2, height=150, width=400, key="t_can", background_color="white")
st.caption("Technician Signature")
can_c = st_canvas(stroke_width=2, height=150, width=400, key="c_can", background_color="white")
st.caption("Customer Signature")

if st.button("🚀 GENERATE PDF REPORT", type="primary", use_container_width=True):
    if not cb:
        st.error("Please enter Technician Name!")
    else:
        # Gunakan logo.png di folder lokal (otomatis)
        logo_path = "logo.png" 
        
        report_photos = []
        for i, pf in enumerate(photo_files):
            img = Image.open(pf)
            img.thumbnail((800, 800))
            report_photos.append({'img': img, 'cap': caps[i]})
        
        s_t = Image.fromarray(can_t.image_data.astype('uint8')) if can_t.image_data is not None else None
        s_c = Image.fromarray(can_c.image_data.astype('uint8')) if can_c.image_data is not None else None
        
        bundle = {'cb':cb, 'cu':cu, 'mw':mw, 'rd':str(rd), 'ma':ma, 'ty':ty, 'sn':sn, 'pr':pr, 'fu':fu}
        pdf_bytes = create_pdf(bundle, s_t, s_c, logo_path, report_photos)
        
        st.session_state['final_pdf'] = pdf_bytes
        st.success("PDF Ready for Download!")

if 'final_pdf' in st.session_state:
    st.download_button("📥 DOWNLOAD PDF", data=st.session_state['final_pdf'], file_name=f"Report_{rd}.pdf", use_container_width=True)
