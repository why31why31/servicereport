import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- 1. TEXT CLEANING (PREVENT UNICODE ERRORS) ---
def clean_text(text):
    if not text: return ""
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '*', '\xb0': ' deg '
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- 2. IMAGE OPTIMIZATION ---
def optimize_image(uploaded_file, max_res=(600, 600)):
    if uploaded_file is None: return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail(max_res, Image.Resampling.LANCZOS)
    return img

# --- 3. PDF CLASS (HEADER ON PAGE 1 ONLY) ---
class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            if self.logo_img:
                w_orig, h_orig = self.logo_img.size
                logo_h = 20 
                logo_w = (w_orig / h_orig) * logo_h
                x_centered = (210 - logo_w) / 2
                self.image(self.logo_img, x=x_centered, y=8, h=logo_h)
                self.ln(logo_h + 5)

            self.set_fill_color(41, 128, 185) # Blue
            self.set_text_color(255, 255, 255) # White
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(3)
        else:
            self.ln(5)

# --- 4. CORE PDF GENERATION FUNCTION ---
def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    # --- INFO BOX ---
    pdf.set_font("helvetica", 'B', 8)
    pdf.set_fill_color(240, 240, 240)
    h_row = 7
    d = {k: clean_text(str(v)) for k, v in data.items()}

    # Row 1
    pdf.cell(30, h_row, " Technician", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Completed By')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Customer", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Customer')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Row 2
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Meet With", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Meet With')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Date", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Date')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Row 3
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Machine", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Machine')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(15, h_row, " Type", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(30, h_row, f" {d.get('Type')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(20, h_row, " Ser No", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(30, h_row, f" {d.get('Serial No')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)
    
    # --- REPORT CONTENT ---
    pdf.set_draw_color(41, 128, 185)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, d.get('Problem'), border=0)
    pdf.ln(3)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, d.get('Follow Up'), border=0)

    # --- ATTACHMENTS (GRID 2x2) ---
    if extra_items:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(0, 10, "DOCUMENTATION PHOTOS", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        cw, rh, gap = 90, 70, 10
        for i, item in enumerate(extra_items):
            if i > 0 and i % 4 == 0: pdf.add_page()
            col, row = i % 2, (i // 2) % 2
            x_pos, y_pos = 10 + (col * (cw + gap)), 30 + (row * (rh + 15))
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x_pos, y_pos, cw, rh)
            pdf.image(item['img'], x=x_pos+2, y=y_pos+2, w=cw-4, h=rh-10)
            pdf.set_xy(x_pos, y_pos + rh - 6)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(cw, 5, f"Photo {i+1}: {clean_text(item['caption'][:50])}", align='C')
        pdf.ln(20)

    # --- SIGNATURES (ALWAYS ON LAST PAGE) ---
    if pdf.get_y() > 230: pdf.add_page()
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(95, 7, "Service Technician,", align='C')
    pdf.cell(95, 7, "Customer / PIC,", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    y_sig = pdf.get_y()
    if sig_t: pdf.image(sig_t, x=42, y=y_sig, w=25)
    if sig_c: pdf.image(sig_c, x=138, y=y_sig, w=25)
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'BU', 9)
    pdf.cell(95, 7, f"{d.get('Completed By')}", align='C')
    pdf.cell(95, 7, f"{d.get('Meet With')}", align='C')

    return bytes(pdf.output())

# --- 5. STREAMLIT UI ---
st.set_page_config(page_title="Digital Service Report", layout="centered")

if st.sidebar.button("🔄 Reset Application"):
    st.session_state.clear()
    st.rerun()

st.title("Digital Service Report")

st.sidebar.header("Media & Branding")
uploaded_logo = st.sidebar.file_uploader("Upload Company Logo (Page 1)", type=["png", "jpg", "jpeg"])
uploaded_photos = st.sidebar.file_uploader("Upload Documentation Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

photo_captions = []
if uploaded_photos:
    st.sidebar.subheader("Photo Captions")
    for i, p in enumerate(uploaded_photos):
        cap = st.sidebar.text_input(f"Caption for Photo {i+1}", key=f"cap_{i}")
        photo_captions.append(cap)

with st.form("main_form"):
    st.subheader("Report Details")
    c1, c2 = st.columns(2)
    with c1:
        comp_by = st.text_input("Completed By")
        cust = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        meet = st.text_input("Meet With")
    with c2:
        rep_date = st.date_input("Date", value=date.today())
        mach = st.text_input("Machine")
        m_type = st.text_input("Type")
        s_no = st.text_input("Serial No")

    prob = st.text_area("Problem Description")
    f_up = st.text_area("Report / Follow Up Action")
    
    st.write("---")
    cs1, cs2 = st.columns(2)
    with cs1:
        st.write("Technician Signature:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=100, width=200, key="c_t")
    with cs2:
        st.write("Customer Signature:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=100, width=200, key="c_c")

    submitted = st.form_submit_button("Generate & Preview")

if submitted:
    if not comp_by: st.error("Technician name is required!")
    else:
        final_photos = []
        if uploaded_photos:
            for idx, p_file in enumerate(uploaded_photos):
                opt_img = optimize_image(p_file)
                final_photos.append({'img': opt_img, 'caption': photo_captions[idx]})
        
        logo_img = Image.open(uploaded_logo) if uploaded_logo else None
        sig_t = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        sig_c = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
        
        rep_data = {
            "Completed By": comp_by, "Customer": cust, "Meet With": meet,
            "Date": str(rep_date), "Machine": mach, "Type": m_type,
            "Serial No": s_no, "Problem": prob, "Follow Up": f_up
        }
        st.session_state.update({'d': rep_data, 'st': sig_t, 'sc': sig_c, 'l': logo_img, 'p': final_photos})
        st.success("Report Generated!")

if 'd' in st.session_state:
    st.write("---")
    pdf_bytes = create_pdf(st.session_state['d'], st.session_state['st'], st.session_state['sc'], logo=st.session_state.get('l'), extra_items=st.session_state.get('p'))
    st.download_button("⬇️ Download PDF Report", data=pdf_bytes, file_name=f"Report_{st.session_state['d']['Serial No']}.pdf")
    
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000" type="application/pdf"></iframe>', unsafe_allow_html=True)
