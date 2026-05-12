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
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- 1. CONFIG & API SETUP ---
# Pastikan Anda sudah memasukkan data JSON ke Streamlit Secrets Dashboard
SHEET_NAME = "Service Report Log" # Nama Google Sheets Anda
FOLDER_ID = "1CODLFKhki8SUL4Ijr7XaqE-x9tQjb6ev" # Ganti dengan ID folder GDrive Anda

def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            return gspread.authorize(creds), creds
    except Exception as e:
        st.sidebar.error(f"Koneksi API Gagal: {e}")
    return None, None

# --- 2. UTILS ---
def clean_text(text):
    if not text: return ""
    replacements = {'\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'", '\xb0': ' deg '}
    for search, replace in replacements.items():
        text = text.replace(search, replace)
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
            self.set_fill_color(41, 128, 185)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(2)

# --- 4. DRIVE & PDF FUNCTIONS ---
def upload_to_drive(pdf_bytes, filename, creds):
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(240, 240, 240)
    h_row = 6.5
    d = {k: clean_text(str(v)) for k, v in data.items()}

    def draw_cell(label, value, wl, wv, last=False):
        pdf.set_font("helvetica", 'B', 8)
        pdf.cell(wl-3, h_row, f" {label}", fill=True); pdf.cell(3, h_row, ":", fill=True, align='C')
        pdf.set_font("helvetica", '', 8)
        x, y = pdf.get_x(), pdf.get_y()
        pdf.cell(wv, h_row, f" {value}")
        pdf.set_line_width(0.05); pdf.line(x+1, y+h_row-1.2, x+wv-1, y+h_row-1.2)
        if last: pdf.ln(h_row)

    # Grid Info (Sejajar & Rapi)
    draw_cell("Technician", d.get('Tech'), 25, 65); draw_cell("Date", d.get('Date'), 25, 65, True)
    draw_cell("Customer", d.get('Cust'), 25, 65); draw_cell("Meet With", d.get('Meet'), 25, 65, True)
    draw_cell("Machine", d.get('Mach'), 25, 50); draw_cell("Type", d.get('Type'), 12, 40); draw_cell("Ser No", d.get('SN'), 18, 35, True)
    
    pdf.ln(4); pdf.set_draw_color(41, 128, 185); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9); pdf.multi_cell(0, 5, d.get('Prob')); pdf.ln(2)
    pdf.cell(0, 7, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.multi_cell(0, 5, d.get('Action')); pdf.ln(4)

    if extra_items:
        if pdf.get_y() > 210: pdf.add_page()
        pdf.set_font("helvetica", 'B', 10); pdf.cell(0, 8, "Attachments Pic", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(3)
        cw, rh, gap = 85, 58, 10
        mx, ry = (210-(cw*2+gap))/2, pdf.get_y()
        for i, item in enumerate(extra_items):
            if i>0 and i%4==0: pdf.add_page(); ry = 25
            elif i>0 and i%2==0: ry += rh + 12
            col = i % 2; xp = mx + (col*(cw+gap))
            pdf.set_draw_color(200, 200, 200); pdf.rect(xp, ry, cw, rh)
            pdf.image(item['img'], x=xp+1, y=ry+1, w=cw-2, h=rh-8)
            pdf.set_xy(xp, ry+rh-5); pdf.set_font("helvetica", 'I', 7); pdf.cell(cw, 5, f"Photo {i+1}", align='C')
            pdf.set_y(ry+rh+8)

    if pdf.get_y() > 240: pdf.add_page()
    pdf.ln(5); pdf.set_font("helvetica", 'B', 9); sy = pdf.get_y()
    pdf.set_xy(10, sy); pdf.cell(95, 7, "Service Technician,", align='C')
    pdf.set_xy(105, sy); pdf.cell(95, 7, "Customer,", align='C')
    if sig_t: pdf.image(sig_t, x=45, y=sy+8, w=25)
    if sig_c: pdf.image(sig_c, x=140, y=sy+8, w=25)
    pdf.set_font("helvetica", 'BU', 9); pdf.set_xy(10, sy+26); pdf.cell(95, 7, f"{d.get('Tech')}", align='C')
    pdf.set_xy(105, sy+26); pdf.cell(95, 7, f"{d.get('Meet')}", align='C')
    return bytes(pdf.output())

# --- 5. UI ---
st.set_page_config(page_title="Finpac Service Report", layout="centered")
client, creds = get_gspread_client()
LOCAL_LOGO = "logo.png"
def_logo = optimize_image(LOCAL_LOGO)

st.title("Digital Service Report")
if client: st.sidebar.success("✅ Google API Connected")
else: st.sidebar.warning("⚠️ API Credentials Belum Terpasang di Secrets")

with st.form("main"):
    c1, c2 = st.columns(2)
    with c1:
        cb = st.text_input("Technician")
        cu = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        mw = st.text_input("Meet With")
        stat = st.selectbox("Status", ["Open", "Pending", "Closed"])
    with c2:
        rd = st.date_input("Date", value=date.today())
        ma = st.text_input("Machine")
        ty = st.text_input("Type")
        sn = st.text_input("Serial No")
    pr, fu = st.text_area("Problem Description"), st.text_area("Report Action")
    s1, s2 = st.columns(2)
    with s1: st.write("Tech Sig:"); ct = st_canvas(stroke_width=2, height=80, width=200, key="ct")
    with s2: st.write("Cust Sig:"); cc = st_canvas(stroke_width=2, height=80, width=200, key="cc")
    uploaded_photos = st.file_uploader("Photos", accept_multiple_files=True)

    if st.form_submit_button("Generate & Save to Cloud"):
        if not cb or not client: st.error("Lengkapi Nama atau Periksa API Config")
        else:
            p_list = [{'img': optimize_image(p)} for p in uploaded_photos]
            d_map = {"Tech": cb, "Cust": cu, "Meet": mw, "Date": str(rd), "Mach": ma, "Type": ty, "SN": sn, "Prob": pr, "Action": fu}
            pdf_bytes = create_pdf(d_map, Image.fromarray(ct.image_data.astype('uint8'), 'RGBA'), Image.fromarray(cc.image_data.astype('uint8'), 'RGBA'), def_logo, p_list)
            
            # Save to Drive & Sheets
            try:
                link = upload_to_drive(pdf_bytes, f"Report_{sn}.pdf", creds)
                sheet = client.open(SHEET_NAME).sheet1
                sheet.append_row([str(rd), rd.strftime("%A"), cu, ma, ty, sn, pr, fu, cb, stat, link])
                st.success("✅ Data tersimpan di Spreadsheet & PDF diunggah ke Drive!")
                st.download_button("⬇️ Download PDF Local", data=pdf_bytes, file_name=f"Report_{sn}.pdf")
            except Exception as e:
                st.error(f"Gagal Simpan ke Cloud: {e}")
