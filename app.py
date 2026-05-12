import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIG & CLOUD SETUP ---
SHEET_NAME = "Service Report Log" 

def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            return gspread.authorize(creds)
    except Exception as e:
        st.sidebar.error(f"Koneksi API Gagal: {e}")
    return None

# --- 2. UTILS ---
def clean_text(text):
    if not text: return ""
    replacements = {'\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'", '\xb0': ' deg '}
    for s, r in replacements.items(): text = text.replace(s, r)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def optimize_image(image_input, max_res=(500, 500)):
    if image_input is None: return None
    try:
        img = Image.open(image_input)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail(max_res, Image.Resampling.LANCZOS)
        return img
    except: return None

# --- 3. PDF CLASS ---
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
            self.ln(logo_h + 2)
            self.set_fill_color(41, 128, 185); self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0); self.ln(2)

def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(240, 240, 240); h_row = 6.5
    d = {k: clean_text(str(v)) for k, v in data.items()}

    def draw_aligned_cell(label, value, wl, wv, last=False):
        pdf.set_font("helvetica", 'B', 8)
        pdf.cell(wl - 3, h_row, f" {label}", border=0, fill=True)
        pdf.cell(3, h_row, ":", border=0, fill=True, align='C')
        x, y = pdf.get_x(), pdf.get_y()
        pdf.set_font("helvetica", '', 8); pdf.cell(wv, h_row, f" {value}")
        pdf.set_line_width(0.05); pdf.line(x + 1, y + h_row - 1.2, x + wv - 1, y + h_row - 1.2)
        if last: pdf.ln(h_row)

    draw_aligned_cell("Technician", d.get('Completed By'), 25, 65)
    draw_aligned_cell("Date", d.get('Date'), 25, 65, last=True)
    draw_aligned_cell("Customer", d.get('Customer'), 25, 65)
    draw_aligned_cell("Meet With", d.get('Meet With'), 25, 65, last=True)
    draw_aligned_cell("Machine", d.get('Machine'), 25, 50)
    draw_aligned_cell("Type", d.get('Type'), 12, 40)
    draw_aligned_cell("Ser No", d.get('Serial No'), 18, 35, last=True)
    
    pdf.ln(4); pdf.set_draw_color(41, 128, 185); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9); pdf.multi_cell(0, 5, d.get('Problem')); pdf.ln(2)
    pdf.cell(0, 7, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.multi_cell(0, 5, d.get('Follow Up')); pdf.ln(4)

    if extra_items:
        if pdf.get_y() > 210: pdf.add_page()
        pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 8, "Attachments Pic", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(3)
        cw, rh = 85, 58; m_x = (210 - (cw * 2 + 10)) / 2; row_y = pdf.get_y()
        for i, item in enumerate(extra_items):
            if i > 0 and i % 4 == 0: pdf.add_page(); row_y = 25
            elif i > 0 and i % 2 == 0: row_y += rh + 12
            col = i % 2; x_p = m_x + (col * (cw + 10))
            pdf.set_draw_color(200, 200, 200); pdf.rect(x_p, row_y, cw, rh)
            pdf.image(item['img'], x=x_p+1, y=row_y+1, w=cw-2, h=rh-8)
            pdf.set_xy(x_p, row_y + rh - 5); pdf.set_font("helvetica", 'I', 7)
            pdf.cell(cw, 5, f"Photo {i+1}: {clean_text(item['caption'][:40])}", align='C')
            pdf.set_y(row_y + rh + 8)

    # --- LOGIKA TANDA TANGAN (LOCK DI BAWAH & TRANSPARAN) ---
    if pdf.get_y() > 220: pdf.add_page()
    pdf.set_y(240) 
    pdf.set_font("helvetica", 'B', 9); sy = pdf.get_y()
    pdf.set_xy(15, sy); pdf.cell(90, 7, "Service Technician,", align='C')
    pdf.set_xy(105, sy); pdf.cell(90, 7, "Customer,", align='C')
    if sig_t: pdf.image(sig_t, x=45, y=sy + 7, w=30)
    if sig_c: pdf.image(sig_c, x=135, y=sy + 7, w=30)
    pdf.set_font("helvetica", 'BU', 9); pdf.set_xy(15, sy + 28); pdf.cell(90, 7, f"{d.get('Completed By')}", align='C')
    pdf.set_xy(105, sy + 28); pdf.cell(90, 7, f"{d.get('Meet With')}", align='C')
    return bytes(pdf.output())

# --- 5. UI & LOGIC ---
st.set_page_config(page_title="Finpac Service Report", layout="centered")

# CSS Agar Canvas Transparan terlihat kotaknya
st.markdown("""
    <style>
    iframe[title="streamlit_drawable_canvas.st_canvas"] { border: 1px solid #ddd !important; background-color: #fff !important; }
    </style>
    """, unsafe_allow_html=True)

client = get_gspread_client()
st.title("Digital Service Report")

uploaded_logo = st.sidebar.file_uploader("Ganti Logo", type=["png", "jpg"])
uploaded_photos = st.sidebar.file_uploader("Photos", type=["png", "jpg"], accept_multiple_files=True)
photo_caps = []
if uploaded_photos:
    for i, _ in enumerate(uploaded_photos):
        photo_caps.append(st.sidebar.text_input(f"Caption Foto {i+1}", key=f"cap_{i}"))

with st.form("main_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        cb = st.text_input("Completed By", key="cb_in")
        cu = st.text_input("Customer", key="cu_in")
        mw = st.text_input("Meet With", key="mw_in")
        status = st.selectbox("Status", ["Open", "Pending", "Closed"], key="st_in")
    with c2:
        rd = st.date_input("Date", value=date.today(), key="rd_in")
        ma = st.text_input("Machine", key="ma_in")
        ty = st.text_input("Type", key="ty_in")
        sn = st.text_input("Serial No", key="sn_in")
    pr, fu = st.text_area("Problem Description", key="pr_in"), st.text_area("Report Action", key="fu_in")
    st.write("---")
    s1, s2 = st.columns(2)
    # Background "rgba(0,0,0,0)" agar tidak ada kotak abu-abu di PDF
    with s1: ct = st_canvas(stroke_width=2, height=80, width=200, key="ct_can", background_color="rgba(0,0,0,0)")
    with s2: cc = st_canvas(stroke_width=2, height=80, width=200, key="cc_can", background_color="rgba(0,0,0,0)")
    
    if st.form_submit_button("1. Generate PDF"):
        if not cb: st.error("Nama Technician harus diisi")
        else:
            logo = optimize_image(uploaded_logo) if uploaded_logo else optimize_image("logo.png")
            final_p = [{'img': optimize_image(p), 'caption': photo_caps[idx] if idx < len(photo_caps) else ""} for idx, p in enumerate(uploaded_photos)]
            d_dict = {"Completed By": cb, "Customer": cu, "Meet With": mw, "Date": str(rd), "Machine": ma, "Type": ty, "Serial No": sn, "Problem": pr, "Follow Up": fu}
            sig_t = Image.fromarray(ct.image_data.astype('uint8'), 'RGBA') if ct.image_data is not None else None
            sig_c = Image.fromarray(cc.image_data.astype('uint8'), 'RGBA') if cc.image_data is not None else None
            
            st.session_state['pdf'] = create_pdf(d_dict, sig_t, sig_c, logo, final_p)
            st.session_state['row_data'] = [str(rd), rd.strftime("%A"), cu, ma, ty, sn, pr, fu, cb, status]
            st.session_state['download_name'] = f"Report_{cu}_{str(rd)}.pdf"
            st.success("✅ PDF Berhasil dibuat!")

if 'pdf' in st.session_state and 'download_name' in st.session_state:
    st.write("---")
    st.download_button("⬇️ Download PDF", data=st.session_state['pdf'], file_name=st.session_state['download_name'])
    manual_link = st.text_input("Masukkan Link GDrive PDF di sini:", key="manual_link_in")
    
    if st.button("2. Simpan & Reset Form"):
        if not manual_link: st.warning("Masukkan link GDrive dahulu.")
        elif client:
            try:
                sheet = client.open(SHEET_NAME).sheet1
                display_name = f"{st.session_state['row_data'][2]} ({st.session_state['row_data'][0]})"
                link_formula = f'=HYPERLINK("{manual_link}", "{display_name}")'
                full_row = st.session_state['row_data'] + [link_formula]
                sheet.append_row(full_row, value_input_option='USER_ENTERED')
                sheet.sort((1, 'asc'), range='A2:K2000')
                st.success("✅ Data tersimpan!")
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
            except Exception as e: st.error(f"Gagal: {e}")
