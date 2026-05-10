import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- 1. PEMBERSIHAN TEKS & OPTIMASI ---
def clean_text(text):
    if not text: return ""
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '*', '\xb0': ' deg '
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def optimize_image(uploaded_file, max_res=(600, 600)):
    if uploaded_file is None: return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail(max_res, Image.Resampling.LANCZOS)
    return img

# --- 2. CLASS PDF (Kop Surat Muncul di Semua Halaman) ---
class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Logo muncul di SETIAP halaman sebagai kop fix
        if self.logo_img:
            w_orig, h_orig = self.logo_img.size
            logo_h = 20 
            logo_w = (w_orig / h_orig) * logo_h
            x_centered = (210 - logo_w) / 2
            self.image(self.logo_img, x=x_centered, y=8, h=logo_h)
            self.ln(logo_h + 5)

        # Banner hanya di halaman pertama (opsional, jika ingin di semua halaman hapus if)
        if self.page_no() == 1:
            self.set_fill_color(41, 128, 185) 
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(3)

# --- 3. FUNGSI UTAMA PDF ---
def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    # --- DATA TEKNIS ---
    pdf.set_font("helvetica", 'B', 8)
    pdf.set_fill_color(240, 240, 240)
    h_row = 7
    
    fields = [
        clean_text(data.get('Completed By', '')), clean_text(data.get('Customer', '')),
        clean_text(data.get('Meet With', '')), clean_text(data.get('Date', '')),
        clean_text(data.get('Machine', '')), clean_text(data.get('Type', '')),
        clean_text(data.get('Serial No', ''))
    ]

    pdf.cell(30, h_row, " Technician", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {fields[0]}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Customer", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {fields[1]}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Meet With", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {fields[2]}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Date", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {fields[3]}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Machine", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {fields[4]}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(15, h_row, " Type", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(30, h_row, f" {fields[5]}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(20, h_row, " Ser No", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(30, h_row, f" {fields[6]}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)
    
    # --- ISI LAPORAN ---
    pdf.set_draw_color(41, 128, 185)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, clean_text(data.get('Problem', '')), border=0)
    pdf.ln(3)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, clean_text(data.get('Follow Up', '')), border=0)

    # --- LAMPIRAN FOTO ---
    if extra_items:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(0, 10, "DOCUMENTATION PHOTOS", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        cw, rh, gap = 90, 70, 10
        for i, item in enumerate(extra_items):
            if i > 0 and i % 4 == 0: pdf.add_page()
            col, row = i % 2, (i // 2) % 2
            x_pos, y_pos = 10 + (col * (cw + gap)), 40 + (row * (rh + 15))
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x_pos, y_pos, cw, rh)
            pdf.image(item['img'], x=x_pos+2, y=y_pos+2, w=cw-4, h=rh-10)
            pdf.set_xy(x_pos, y_pos + rh - 6)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(cw, 5, f"Photo {i+1}: {clean_text(item['caption'][:50])}", align='C')
        pdf.ln(20)

    # --- TANDA TANGAN ---
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
    pdf.cell(95, 7, f"{fields[0]}", align='C')
    pdf.cell(95, 7, f"{fields[2]}", align='C')

    return bytes(pdf.output())

# --- 4. UI STREAMLIT ---
st.set_page_config(page_title="Service Report System", layout="centered")

st.sidebar.title("Pengaturan Kop")
uploaded_logo = st.sidebar.file_uploader("Upload Logo Baru (Ganti Kop)", type=["png", "jpg", "jpeg"])
uploaded_photos = st.sidebar.file_uploader("Tambah Foto Dokumentasi", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

photo_data = []
if uploaded_photos:
    for i, p in enumerate(uploaded_photos):
        cap = st.sidebar.text_input(f"Keterangan Foto {i+1}", key=f"cap_{i}")
        photo_data.append({'file': p, 'caption': cap})

with st.form("main_form"):
    st.subheader("Data Laporan")
    c1, c2 = st.columns(2)
    with c1:
        comp_by = st.text_input("Completed By")
        cust = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        meet = st.text_input("Meet With")
    with c2:
        dt = st.date_input("Date", value=date.today())
        mach = st.text_input("Machine")
        stype = st.text_input("Type")
        ser = st.text_input("Serial No")

    prob = st.text_area("Problem Description")
    fup = st.text_area("Report / Follow Up Action")
    
    st.write("---")
    cs1, cs2 = st.columns(2)
    with cs1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=100, width=200, key="c_t")
    with cs2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=100, width=200, key="c_c")

    sub = st.form_submit_button("Simpan & Preview")

if sub:
    if not comp_by: st.error("Nama Teknisi harus diisi!")
    else:
        # Generate Data
        logo_img = Image.open(uploaded_logo) if uploaded_logo else None
        final_photos = [{'img': optimize_image(i['file']), 'caption': i['caption']} for i in photo_data]
        sig_t = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        sig_c = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
        
        rep_data = {
            "Completed By": comp_by, "Customer": cust, "Meet With": meet,
            "Date": str(dt), "Machine": mach, "Type": stype, "Serial No": ser,
            "Problem": prob, "Follow Up": fup
        }
        st.session_state.update({'d': rep_data, 'st': sig_t, 'sc': sig_c, 'l': logo_img, 'p': final_photos})
        st.success("Laporan diproses!")

if 'd' in st.session_state:
    pdf_bytes = create_pdf(st.session_state['d'], st.session_state['st'], st.session_state['sc'], logo=st.session_state.get('l'), extra_items=st.session_state.get('p'))
    
    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=f"Report_{st.session_state['d']['Serial No']}.pdf")
    
    # Preview Full Halaman
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
