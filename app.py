import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
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

# --- 2. PDF ENGINE (REBUILT) ---
class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img
        self.set_margin(15)

    def header(self):
        # Header HANYA di halaman pertama
        if self.page_no() == 1:
            if self.logo_img:
                # Menghitung posisi tengah untuk logo
                w_orig, h_orig = self.logo_img.size
                logo_h = 18
                logo_w = (w_orig / h_orig) * logo_h
                self.image(self.logo_img, x=(210 - logo_w) / 2, y=10, h=logo_h)
                self.set_y(32)
            else:
                self.set_y(15)
            
            # Judul Laporan
            self.set_fill_color(41, 128, 185)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(5)

def create_pdf(data, s_t, s_c, logo, photos):
    pdf = PDF(logo_img=logo)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # 1. Information Table (Dibuat lebih rapi agar tidak berantakan)
    pdf.set_font("helvetica", 'B', 9)
    pdf.set_fill_color(245, 245, 245)
    
    # Baris 1
    pdf.cell(30, 8, " Technician:", fill=True); pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['cb']}", border='B')
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(30, 8, " Date:", fill=True); pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['rd']}", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Baris 2
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(30, 8, " Customer:", fill=True); pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['cu']}", border='B')
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(30, 8, " Contact:", fill=True); pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['mw']}", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Baris 3
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(30, 8, " Machine:", fill=True); pdf.set_font("helvetica", '', 9)
    pdf.cell(40, 8, f" {data['ma']}", border='B')
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(20, 8, " Type:", fill=True); pdf.set_font("helvetica", '', 9)
    pdf.cell(40, 8, f" {data['ty']}", border='B')
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(15, 8, " SN:", fill=True); pdf.set_font("helvetica", '', 9)
    pdf.cell(35, 8, f" {data['sn']}", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)

    # 2. Problem & Action
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['pr'])
    pdf.ln(4)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['fu'])
    pdf.ln(10)

    # 3. Attachments (Sistem Grid yang lebih stabil)
    if photos:
        # Cek jika sisa halaman terlalu sempit untuk judul lampiran
        if pdf.get_y() > 200: pdf.add_page()
        
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 8, "ATTACHMENTS / PHOTOS", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        
        img_w, img_h = 85, 60
        margin_x = 15
        
        for i, p in enumerate(photos):
            # Cek sisa ruang sebelum menggambar baris baru
            if i % 2 == 0 and (pdf.get_y() + img_h + 15) > 275:
                pdf.add_page()
            
            curr_x = margin_x if i % 2 == 0 else 110
            curr_y = pdf.get_y()
            
            # Bingkai Foto
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(curr_x, curr_y, img_w, img_h)
            
            # Gambar
            pdf.image(p['img'], x=curr_x+1, y=curr_y+1, w=img_w-2, h=img_h-8)
            
            # Keterangan Foto
            pdf.set_xy(curr_x, curr_y + img_h - 6)
            pdf.set_font("helvetica", 'I', 8)
            pdf.cell(img_w, 5, f"Photo {i+1}: {p['cap']}", align='C')
            
            # Pindah baris setelah 2 foto
            if i % 2 == 1 or i == len(photos)-1:
                pdf.set_y(curr_y + img_h + 10)

    # 4. Signatures (Dipaksa ke bagian bawah halaman terakhir)
    if pdf.get_y() > 230: pdf.add_page()
    pdf.set_y(245)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(90, 7, "Service Technician,", align='C')
    pdf.cell(90, 7, "Customer,", align='C')
    
    if s_t: pdf.image(s_t, x=45, y=252, w=30)
    if s_c: pdf.image(s_c, x=135, y=252, w=30)
    
    pdf.set_y(275)
    pdf.set_font("helvetica", 'BU', 10)
    pdf.cell(90, 7, data['cb'], align='C')
    pdf.cell(90, 7, data['mw'], align='C')
    
    return bytes(pdf.output())

# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="Service Report", layout="centered")

# Custom CSS
st.markdown("<style>iframe{border:1px solid #ddd !important; border-radius:10px; background-color:white;}</style>", unsafe_allow_html=True)

st.title("Digital Service Report")
client = get_gspread_client()

# Sidebar
with st.sidebar:
    st.header("Upload Media")
    logo_file = st.file_uploader("Upload Company Logo", type=["png", "jpg"])
    st.write("---")
    photo_files = st.file_uploader("Upload Report Photos", type=["jpg", "png"], accept_multiple_files=True)
    caps = [st.text_input(f"Caption {i+1}", key=f"c_{i}") for i in range(len(photo_files))]

# Input Data
col1, col2 = st.columns(2)
with col1:
    cb = st.text_input("Technician Name")
    cu = st.text_input("Customer Name", value="PT. Finpac Anugerah Indonesia")
    mw = st.text_input("Meet With")
    status = st.selectbox("Status", ["Open", "Pending", "Closed"])
with col2:
    rd = st.date_input("Date", value=date.today())
    ma = st.text_input("Machine")
    ty = st.text_input("Type")
    sn = st.text_input("Serial No")

pr = st.text_area("Problem Description")
fu = st.text_area("Action Taken / Follow Up")

st.write("---")
st.write("### Signatures")
can_t = st_canvas(stroke_width=2, height=150, width=500, key="t_can", background_color="white")
st.caption("Technician Signature")
can_c = st_canvas(stroke_width=2, height=150, width=500, key="c_can", background_color="white")
st.caption("Customer Signature")

if st.button("🚀 GENERATE PDF REPORT", type="primary", use_container_width=True):
    if not cb:
        st.error("Please fill in Technician Name!")
    else:
        # Process Images
        logo = Image.open(logo_file) if logo_file else None
        report_photos = []
        for i, pf in enumerate(photo_files):
            img = Image.open(pf)
            img.thumbnail((800, 800))
            report_photos.append({'img': img, 'cap': caps[i]})
        
        # Process Sigs
        s_t = Image.fromarray(can_t.image_data.astype('uint8')) if can_t.image_data is not None else None
        s_c = Image.fromarray(can_c.image_data.astype('uint8')) if can_c.image_data is not None else None
        
        bundle = {'cb':cb, 'cu':cu, 'mw':mw, 'rd':str(rd), 'ma':ma, 'ty':ty, 'sn':sn, 'pr':pr, 'fu':fu}
        pdf_bytes = create_pdf(bundle, s_t, s_c, logo, report_photos)
        
        st.session_state['final_pdf'] = pdf_bytes
        st.session_state['save_row'] = [str(rd), cu, ma, ty, sn, pr, fu, cb, status]
        st.success("PDF Generated Successfully!")

if 'final_pdf' in st.session_state:
    st.download_button("📥 DOWNLOAD PDF", data=st.session_state['final_pdf'], file_name=f"Report_{rd}.pdf", use_container_width=True)
    g_link = st.text_input("Paste GDrive Link:")
    if st.button("💾 SAVE & RESET", use_container_width=True):
        if client:
            sheet = client.open(SHEET_NAME).sheet1
            sheet.append_row(st.session_state['save_row'] + [g_link])
            st.success("Saved!")
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
