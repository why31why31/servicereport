import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CLOUD CONNECTION ---
SHEET_NAME = "Service Report Log" 

def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            return gspread.authorize(creds)
    except Exception as e:
        return None

# --- 2. PDF GENERATION LOGIC ---
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
            self.set_fill_color(41, 128, 185)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0); self.ln(5)

def create_pdf(data, sig_t, sig_c, logo, photos):
    pdf = PDF(logo_img=logo)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Information Table
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", 'B', 8)
    
    rows = [
        [("Technician", data['cb']), ("Date", data['rd'])],
        [("Customer", data['cu']), ("Meet With", data['mw'])],
        [("Machine", data['ma']), ("Type", data['ty']), ("Ser No", data['sn'])]
    ]

    for row in rows:
        for label, val in row:
            pdf.set_font("helvetica", 'B', 8)
            pdf.cell(20, 7, f" {label}:", fill=True)
            pdf.set_font("helvetica", '', 8)
            pdf.cell(45 if len(row)==2 else 30, 7, f" {val}", border='B')
        pdf.ln(8)

    # Content Sections
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, data['pr'])
    
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, data['fu'])

    # Photos Section with Page Break Logic
    if photos:
        if pdf.get_y() > 180: pdf.add_page()
        pdf.ln(10)
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 8, "ATTACHMENTS", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        
        for i, p in enumerate(photos):
            if i % 2 == 0 and pdf.get_y() > 210: pdf.add_page()
            
            x_pos = 15 if i % 2 == 0 else 110
            y_start = pdf.get_y()
            
            pdf.image(p['img'], x=x_pos, y=y_start, w=85, h=60)
            pdf.set_xy(x_pos, y_start + 62)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(85, 5, f"Photo {i+1}: {p['cap'][:40]}", align='C')
            
            if i % 2 == 1 or i == len(photos)-1:
                pdf.set_y(y_start + 75)

    # Signatures - Forced to bottom
    if pdf.get_y() > 220: pdf.add_page()
    pdf.set_y(240)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(90, 7, "Service Technician,", align='C')
    pdf.cell(90, 7, "Customer,", align='C')
    
    if sig_t: pdf.image(sig_t, x=45, y=247, w=30)
    if sig_c: pdf.image(sig_c, x=135, y=247, w=30)
    
    pdf.set_y(270)
    pdf.set_font("helvetica", 'BU', 9)
    pdf.cell(90, 7, data['cb'], align='C')
    pdf.cell(90, 7, data['mw'], align='C')
    
    return bytes(pdf.output())

# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="Finpac Service Report", layout="centered")

# CSS to make the signature boxes visible
st.markdown("<style>iframe{border:1px solid #ccc !important; border-radius:5px;}</style>", unsafe_allow_html=True)

client = get_gspread_client()
st.title("Digital Service Report")

# Sidebar for Assets
with st.sidebar:
    st.header("Settings & Media")
    logo_file = st.file_uploader("Company Logo", type=["png", "jpg"])
    photo_files = st.file_uploader("Report Photos", type=["jpg", "png"], accept_multiple_files=True)
    caps = [st.text_input(f"Caption {i+1}", key=f"c{i}") for i, _ in enumerate(photo_files)] if photo_files else []

# Form for Text Data
with st.form("data_form"):
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
    fu = st.text_area("Action Taken")
    
    st.info("Fill out form above, sign below, then click Generate.")
    submitted = st.form_submit_button("Confirm Data")

# Signature Section (Outside form for stability)
st.subheader("Signatures")
sig_col1, sig_col2 = st.columns(2)
with sig_col1:
    st.write("Technician:")
    canvas_t = st_canvas(stroke_width=2, height=120, width=320, key="t_sig", background_color="rgba(0,0,0,0)")
with sig_col2:
    st.write("Customer:")
    canvas_c = st_canvas(stroke_width=2, height=120, width=320, key="c_sig", background_color="rgba(0,0,0,0)")

# PDF Generation
if st.button("Generate & Download PDF", type="primary"):
    if not cb:
        st.error("Please enter Technician Name.")
    else:
        # Process Assets
        logo = Image.open(logo_file) if logo_file else None
        report_photos = []
        for i, pf in enumerate(photo_files):
            img = Image.open(pf)
            img.thumbnail((800, 800))
            report_photos.append({'img': img, 'cap': caps[i]})
        
        # Process Signatures
        s_t = Image.fromarray(canvas_t.image_data.astype('uint8'), 'RGBA') if canvas_t.image_data is not None else None
        s_c = Image.fromarray(canvas_c.image_data.astype('uint8'), 'RGBA') if canvas_c.image_data is not None else None
        
        data_bundle = {'cb':cb, 'cu':cu, 'mw':mw, 'rd':str(rd), 'ma':ma, 'ty':ty, 'sn':sn, 'pr':pr, 'fu':fu}
        
        pdf_bytes = create_pdf(data_bundle, s_t, s_c, logo, report_photos)
        st.session_state['ready_pdf'] = pdf_bytes
        st.session_state['row_to_save'] = [str(rd), cu, ma, ty, sn, pr, fu, cb, status]
        st.success("PDF Generated Successfully!")

# Save & Reset
if 'ready_pdf' in st.session_state:
    st.download_button("Download Document", data=st.session_state['ready_pdf'], file_name=f"Report_{cb}_{rd}.pdf")
    gdrive_link = st.text_input("GDrive Link (Optional for Spreadsheet)")
    
    if st.button("Save to Sheet & Reset"):
        if client:
            sheet = client.open(SHEET_NAME).sheet1
            row = st.session_state['row_to_save'] + [gdrive_link]
            sheet.append_row(row)
            st.success("Data Saved!")
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
