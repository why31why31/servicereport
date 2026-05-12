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
    
    # Information Summary
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(0, 8, f"Technician: {data['cb']} | Date: {data['rd']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Customer: {data['cu']} | Contact: {data['mw']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Machine: {data['ma']} | Type: {data['ty']} | SN: {data['sn']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5); pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 6, data['pr']); pdf.ln(5)
    
    pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 7, "FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10); pdf.multi_cell(0, 6, data['fu'])

    # Photos Section
    if photos:
        if pdf.get_y() > 180: pdf.add_page()
        pdf.ln(10); pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 8, "ATTACHMENTS", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(5)
        for i, p in enumerate(photos):
            if i % 2 == 0 and pdf.get_y() > 210: pdf.add_page()
            x = 15 if i % 2 == 0 else 110
            y_img = pdf.get_y()
            pdf.image(p['img'], x=x, y=y_img, w=85, h=60)
            pdf.set_xy(x, y_img + 62); pdf.set_font("helvetica", 'I', 8); pdf.cell(85, 5, f"Photo {i+1}: {p['cap']}", align='C')
            if i % 2 == 1 or i == len(photos)-1: pdf.set_y(y_img + 75)

    # Signature Section
    if pdf.get_y() > 220: pdf.add_page()
    pdf.set_y(240); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(90, 7, "Technician,", align='C'); pdf.cell(90, 7, "Customer,", align='C')
    if s_t: pdf.image(s_t, x=45, y=247, w=30)
    if s_c: pdf.image(s_c, x=135, y=247, w=30)
    pdf.set_y(270); pdf.cell(90, 7, data['cb'], align='C'); pdf.cell(90, 7, data['mw'], align='C')
    return bytes(pdf.output())

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Service Report", layout="centered")

# CSS for better Iframe and Signature visibility
st.markdown("<style>iframe{border:1px solid #ddd !important; border-radius:8px; width:100% !important; background-color: white;}</style>", unsafe_allow_html=True)

st.title("Digital Service Report")
client = get_gspread_client()

# --- SIDEBAR (RESTORED) ---
with st.sidebar:
    st.header("Media Upload")
    logo_file = st.file_uploader("Upload Company Logo", type=["png", "jpg"])
    st.write("---")
    photo_files = st.file_uploader("Upload Report Photos", type=["jpg", "png"], accept_multiple_files=True)
    
    caps = []
    if photo_files:
        st.subheader("Photo Captions")
        for i, pf in enumerate(photo_files):
            caps.append(st.text_input(f"Caption for Photo {i+1}", key=f"cap_sb_{i}"))

# --- DATA INPUT ---
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

# Technician Canvas
st.write("**Technician Signature:**")
can_t = st_canvas(stroke_width=2, height=150, width=500, key="t_can_final", background_color="white", display_toolbar=True)

# Customer Canvas
st.write("**Customer Signature:**")
can_c = st_canvas(stroke_width=2, height=150, width=500, key="c_can_final", background_color="white", display_toolbar=True)

# Main Generation Button
if st.button("🚀 GENERATE PDF REPORT", type="primary", use_container_width=True):
    if not cb:
        st.error("Please enter Technician Name!")
    else:
        # Image Processing
        logo = Image.open(logo_file) if logo_file else None
        report_photos = []
        for i, pf in enumerate(photo_files):
            img = Image.open(pf)
            img.thumbnail((800, 800))
            report_photos.append({'img': img, 'cap': caps[i] if i < len(caps) else ""})
        
        # Signature Processing
        s_t = Image.fromarray(can_t.image_data.astype('uint8')) if can_t.image_data is not None else None
        s_c = Image.fromarray(can_c.image_data.astype('uint8')) if can_c.image_data is not None else None
        
        data_bundle = {'cb':cb, 'cu':cu, 'mw':mw, 'rd':str(rd), 'ma':ma, 'ty':ty, 'sn':sn, 'pr':pr, 'fu':fu}
        
        pdf_out = create_pdf(data_bundle, s_t, s_c, logo, report_photos)
        st.session_state['pdf_done'] = pdf_out
        st.session_state['save_data'] = [str(rd), cu, ma, ty, sn, pr, fu, cb, status]
        st.success("PDF Created Successfully!")

# Download and Spreadsheet Save
if 'pdf_done' in st.session_state:
    st.write("---")
    st.download_button("📥 DOWNLOAD PDF", data=st.session_state['pdf_done'], file_name=f"Report_{rd}.pdf", use_container_width=True)
    
    g_link = st.text_input("Paste GDrive PDF Link here:")
    if st.button("💾 SAVE TO SPREADSHEET & RESET", use_container_width=True):
        if client:
            try:
                sheet = client.open(SHEET_NAME).sheet1
                sheet.append_row(st.session_state['save_data'] + [g_link])
                st.success("Data saved successfully!")
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
            except Exception as e:
                st.error(f"Spreadsheet Error: {e}")
