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

# --- 2. PDF ENGINE ---
class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img
        self.set_margin(15)

    def header(self):
        if self.page_no() == 1 and self.logo_img:
            w_orig, h_orig = self.logo_img.size
            logo_h = 18
            logo_w = (w_orig / h_orig) * logo_h
            self.image(self.logo_img, x=(210 - logo_w) / 2, y=8, h=logo_h)
            self.ln(20)
            self.set_fill_color(41, 128, 185); self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0); self.ln(5)

def create_pdf(data, s_t, s_c, logo, photos):
    pdf = PDF(logo_img=logo)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Grid Data
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(0, 8, f"Technician: {data['cb']} | Date: {data['rd']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Customer: {data['cu']} | Meet With: {data['mw']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Machine: {data['ma']} | Type: {data['ty']} | SN: {data['sn']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5); pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 6, data['pr']); pdf.ln(5)
    
    pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 7, "FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 6, data['fu'])

    # Photos with overflow fix
    if photos:
        if pdf.get_y() > 180: pdf.add_page()
        pdf.ln(10); pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 8, "ATTACHMENTS", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(5)
        for i, p in enumerate(photos):
            if i % 2 == 0 and pdf.get_y() > 210: pdf.add_page()
            x = 15 if i % 2 == 0 else 110
            y = pdf.get_y()
            pdf.image(p['img'], x=x, y=y, w=85, h=60)
            pdf.set_xy(x, y + 62); pdf.set_font("helvetica", 'I', 8); pdf.cell(85, 5, f"Photo {i+1}: {p['cap']}", align='C')
            if i % 2 == 1 or i == len(photos)-1: pdf.set_y(y + 75)

    # Signatures
    if pdf.get_y() > 220: pdf.add_page()
    pdf.set_y(240); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(90, 7, "Technician,", align='C'); pdf.cell(90, 7, "Customer,", align='C')
    if s_t: pdf.image(s_t, x=45, y=247, w=30)
    if s_c: pdf.image(s_c, x=135, y=247, w=30)
    pdf.set_y(270); pdf.cell(90, 7, data['cb'], align='C'); pdf.cell(90, 7, data['mw'], align='C')
    return bytes(pdf.output())

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Service Report", layout="centered")

# Fix for Signature Iframe display
st.markdown("<style>iframe{border:1px solid #eee !important; border-radius:10px; width:100% !important;}</style>", unsafe_allow_html=True)

st.title("Digital Service Report")
client = get_gspread_client()

# Data Input (Direct, no Form for stability)
cb = st.text_input("Technician Name")
cu = st.text_input("Customer Name", value="PT. Finpac Anugerah Indonesia")
mw = st.text_input("Meet With")
rd = st.date_input("Date", value=date.today())
ma = st.text_input("Machine")
ty = st.text_input("Type")
sn = st.text_input("Serial No")
pr = st.text_area("Problem Description")
fu = st.text_area("Action Taken")

st.write("---")
# Photos
photo_files = st.file_uploader("Upload Photos", type=["jpg", "png"], accept_multiple_files=True)
caps = [st.text_input(f"Caption {i+1}", key=f"c{i}") for i in range(len(photo_files))]

st.write("---")
# Signatures
st.write("### Signatures")
st.write("Technician:")
can_t = st_canvas(stroke_width=2, height=150, width=500, key="t_can", background_color="white")
st.write("Customer:")
can_c = st_canvas(stroke_width=2, height=150, width=500, key="c_can", background_color="white")

# Main Action Button
if st.button("🚀 GENERATE PDF REPORT", type="primary", use_container_width=True):
    if not cb:
        st.error("Missing Technician Name!")
    else:
        # Process Media
        report_photos = []
        for i, pf in enumerate(photo_files):
            img = Image.open(pf)
            img.thumbnail((800, 800))
            report_photos.append({'img': img, 'cap': caps[i]})
        
        # Process Sigs
        s_t = Image.fromarray(can_t.image_data.astype('uint8')) if can_t.image_data is not None else None
        s_c = Image.fromarray(can_c.image_data.astype('uint8')) if can_c.image_data is not None else None
        
        bundle = {'cb':cb, 'cu':cu, 'mw':mw, 'rd':str(rd), 'ma':ma, 'ty':ty, 'sn':sn, 'pr':pr, 'fu':fu}
        pdf_bytes = create_pdf(bundle, s_t, s_c, None, report_photos)
        
        st.session_state['ready_pdf'] = pdf_bytes
        st.session_state['row'] = [str(rd), cu, ma, ty, sn, pr, fu, cb]
        st.success("PDF Ready!")

# Download & Save
if 'ready_pdf' in st.session_state:
    st.download_button("📥 DOWNLOAD PDF", data=st.session_state['ready_pdf'], file_name=f"Report_{rd}.pdf", use_container_width=True)
    link = st.text_input("GDrive Link")
    if st.button("💾 SAVE TO SPREADSHEET", use_container_width=True):
        if client:
            sheet = client.open(SHEET_NAME).sheet1
            sheet.append_row(st.session_state['row'] + [link])
            st.success("Saved!")
        st.rerun()
