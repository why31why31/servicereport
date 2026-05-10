import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- 1. UTILS & TEXT CLEANING ---
def clean_text(text):
    if not text: return ""
    # Map common non-latin characters to prevent FPDFUnicodeEncodingException
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '*', '\xb0': ' deg '
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def optimize_image(uploaded_file, max_res=(500, 500)):
    """Downscale images to prevent memory 'hangs' and blank previews"""
    if uploaded_file is None: return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail(max_res, Image.Resampling.LANCZOS)
    return img

# --- 2. PDF CLASS ---
class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img
        # Tight bottom margin to maximize space on the last page
        self.set_auto_page_break(auto=True, margin=10)

    def header(self):
        if self.page_no() == 1:
            if self.logo_img:
                w_orig, h_orig = self.logo_img.size
                logo_h = 18
                logo_w = (w_orig / h_orig) * logo_h
                self.image(self.logo_img, x=(210 - logo_w) / 2, y=8, h=logo_h)
                self.ln(logo_h + 2)
            self.set_fill_color(41, 128, 185)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(2)

# --- 3. CORE PDF GENERATION ---
def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    pdf.set_font("helvetica", 'B', 8)
    pdf.set_fill_color(240, 240, 240)
    h_row = 6.5
    d = {k: clean_text(str(v)) for k, v in data.items()}

    # Data Information Grid
    pdf.cell(30, h_row, " Technician", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Completed By')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Customer", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Customer')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.cell(30, h_row, " Meet With", border=1, fill=True)
    pdf.cell(65, h_row, f" {d.get('Meet With')}", border=1)
    pdf.cell(30, h_row, " Date", border=1, fill=True)
    pdf.cell(65, h_row, f" {d.get('Date')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.cell(30, h_row, " Machine", border=1, fill=True)
    pdf.cell(65, h_row, f" {d.get('Machine')}", border=1)
    pdf.cell(15, h_row, " Type", border=1, fill=True)
    pdf.cell(30, h_row, f" {d.get('Type')}", border=1)
    pdf.cell(20, h_row, " Ser No", border=1, fill=True)
    pdf.cell(30, h_row, f" {d.get('Serial No')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(3)
    pdf.set_draw_color(41, 128, 185)
    
    # Problem Description
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 6, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, d.get('Problem'), border=0)
    pdf.ln(2)
    
    # Follow Up Action
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 6, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, d.get('Follow Up'), border=0)
    pdf.ln(3)

    # --- CENTERED IMAGE GRID (2x2) ---
    if extra_items:
        # Check if remaining space is too low, then page break
        if pdf.get_y() > 250: pdf.add_page()
        
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 6, "DOCUMENTATION PHOTOS", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        
        # FIXED: Correct variable unpacking
        cw, rh, gap = 85, 58, 10
        margin_left = (210 - (cw * 2 + gap)) / 2
        
        start_y = pdf.get_y()
        for i, item in enumerate(extra_items):
            if i > 0 and i % 4 == 0:
                pdf.add_page()
                start_y = pdf.get_y() + 5
            
            col, row = i % 2, (i // 2) % 2
            x_pos = margin_left + (col * (cw + gap))
            y_pos = start_y + (row * (rh + 10))
            
            if y_pos + rh > 280:
                pdf.add_page()
                start_y, y_pos = pdf.get_y() + 5, pdf.get_y() + 5
            
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x_pos, y_pos, cw, rh)
            pdf.image(item['img'], x=x_pos+1, y=y_pos+1, w=cw-2, h=rh-8)
            pdf.set_xy(x_pos, y_pos + rh - 6)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(cw, 5, f"Photo {i+1}: {clean_text(item['caption'][:40])}", align='C')
            
            if col == 1 or i == len(extra_items)-1:
                pdf.set_y(y_pos + rh + 5)

    # --- SIGNATURES ---
    # Signature threshold set to 255 to force it on the same page as Photo 3 if space exists
    if pdf.get_y() > 255: pdf.add_page()
    
    pdf.ln(4)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(95, 6, "Service Technician,", align='C')
    pdf.cell(95, 6, "Customer / PIC,", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    y_sig = pdf.get_y()
    if sig_t: pdf.image(sig_t, x=42, y=y_sig, w=25)
    if sig_c: pdf.image(sig_c, x=138, y=y_sig, w=25)
    
    pdf.ln(18)
    pdf.set_font("helvetica", 'BU', 9)
    pdf.cell(95, 6, f"{d.get('Completed By')}", align='C')
    pdf.cell(95, 6, f"{d.get('Meet With')}", align='C')

    return bytes(pdf.output())

# --- 4. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Digital Service Report", layout="centered")

if st.sidebar.button("🔄 Clear Cache & Reset"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

st.title("Digital Service Report")
uploaded_logo = st.sidebar.file_uploader("Company Logo", type=["png", "jpg", "jpeg"])
uploaded_photos = st.sidebar.file_uploader("Documentation Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

photo_caps = []
if uploaded_photos:
    for i, _ in enumerate(uploaded_photos):
        photo_caps.append(st.sidebar.text_input(f"Caption {i+1}", key=f"c_{i}"))

with st.form("main_report"):
    c1, c2 = st.columns(2)
    with c1:
        cb = st.text_input("Completed By")
        cu = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        mw = st.text_input("Meet With")
    with c2:
        rd = st.date_input("Date", value=date.today())
        ma = st.text_input("Machine")
        ty = st.text_input("Type")
        sn = st.text_input("Serial No")
    
    pr = st.text_area("Problem Description")
    fu = st.text_area("Report / Follow Up Action")
    
    st.write("---")
    s1, s2 = st.columns(2)
    with s1: 
        st.write("Technician Signature:")
        ct = st_canvas(stroke_width=2, height=80, width=200, key="ct")
    with s2: 
        st.write("Customer Signature:")
        cc = st_canvas(stroke_width=2, height=80, width=200, key="cc")
    
    if st.form_submit_button("Generate Report"):
        if not cb: st.error("Technician name is required")
        else:
            final_p = [{'img': optimize_image(p), 'caption': photo_caps[idx]} for idx, p in enumerate(uploaded_photos)]
            st.session_state.update({
                'd': {"Completed By": cb, "Customer": cu, "Meet With": mw, "Date": str(rd), "Machine": ma, "Type": ty, "Serial No": sn, "Problem": pr, "Follow Up": fu}, 
                'st': Image.fromarray(ct.image_data.astype('uint8'), 'RGBA') if ct.image_data is not None else None,
                'sc': Image.fromarray(cc.image_data.astype('uint8'), 'RGBA') if cc.image_data is not None else None,
                'l': optimize_image(uploaded_logo), 
                'p': final_p
            })

if 'd' in st.session_state:
    pdf_b = create_pdf(st.session_state['d'], st.session_state['st'], st.session_state['sc'], st.session_state['l'], st.session_state['p'])
    st.download_button("⬇️ Download PDF", data=pdf_b, file_name=f"Report_{st.session_state['d']['Serial No']}.pdf")
    
    base64_pdf = base64.b64encode(pdf_b).decode()
    st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800"></iframe>', unsafe_allow_html=True)
