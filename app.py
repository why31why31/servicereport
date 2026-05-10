import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- KONFIGURASI ---
EXCEL_FILE = "service_reports.xlsx"

class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.page_no() == 1:
            if self.logo_img:
                # Perhitungan center presisi
                w_orig, h_orig = self.logo_img.size
                logo_h = 22 
                logo_w = (w_orig / h_orig) * logo_h
                x_pos = (210 - logo_w) / 2
                self.image(self.logo_img, x=x_pos, y=8, h=logo_h)
                self.ln(logo_h + 2)

            self.set_fill_color(41, 128, 185) 
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(3)

def optimize_image(uploaded_file, max_res=(600, 600)): # Resolusi diperkecil agar tidak blank
    if uploaded_file is None: return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail(max_res, Image.Resampling.LANCZOS)
    return img

def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    # --- INFO BOX ---
    pdf.set_font("helvetica", 'B', 8)
    pdf.set_fill_color(240, 240, 240)
    h_row = 7
    
    # Baris data teknis
    pdf.cell(30, h_row, " Technician", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data.get('Completed By', '')}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(30, h_row, " Customer", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data.get('Customer', '')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.cell(30, h_row, " Meet With", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data.get('Meet With', '')}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(30, h_row, " Date", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data.get('Date', '')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.cell(30, h_row, " Machine", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data.get('Machine', '')}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(15, h_row, " Type", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(30, h_row, f" {data.get('Type', '')}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(20, h_row, " Ser No", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(30, h_row, f" {data.get('Serial No', '')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(4)
    
    # --- ISI LAPORAN ---
    pdf.set_draw_color(41, 128, 185)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, data.get('Problem', ''), border=0)
    pdf.ln(3)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, data.get('Follow Up', ''), border=0)
    pdf.ln(5)

    # --- LAMPIRAN FOTO ---
    if extra_items:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(0, 10, "DOCUMENTATION PHOTOS", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        cw, rh, gap = 90, 75, 10
        for i, item in enumerate(extra_items):
            if i > 0 and i % 4 == 0: pdf.add_page()
            col, row = i % 2, (i // 2) % 2
            x, y = 10 + (col * (cw + gap)), pdf.get_y() if row == 0 else pdf.get_y() - rh - 15 + (row * (rh + 15))
            # Penyesuaian Y dinamis untuk grid
            y_fixed = 30 + (row * (rh + 15))
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x, y_fixed, cw, rh)
            pdf.image(item['img'], x=x+2, y=y_fixed+2, w=cw-4, h=rh-10)
            pdf.set_xy(x, y_fixed + rh - 6)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(cw, 5, f"Photo {i+1}: {item['caption'][:50]}", align='C')
        pdf.ln(20)

    # --- TANDA TANGAN DI HALAMAN TERAKHIR ---
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
    pdf.cell(95, 7, f"{data.get('Completed By', '')}", align='C')
    pdf.cell(95, 7, f"{data.get('Meet With', '')}", align='C')

    return bytes(pdf.output())

# --- UI STREAMLIT ---
st.set_page_config(page_title="Finpac Service Report", layout="centered")

if st.sidebar.button("🔄 Reset Aplikasi"):
    st.session_state.clear()
    st.rerun()

st.title("Digital Service Report")

st.sidebar.header("Media & Settings")
uploaded_logo = st.sidebar.file_uploader("Upload Logo", type=["png", "jpg", "jpeg"])
uploaded_photos = st.sidebar.file_uploader("Pilih Foto Dokumentasi", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

photo_data = []
if uploaded_photos:
    st.sidebar.subheader("Keterangan Lampiran")
    for i, p in enumerate(uploaded_photos):
        cap = st.sidebar.text_input(f"Ket Foto {i+1}", key=f"cap_{i}")
        photo_data.append({'file': p, 'caption': cap})

with st.form("main_form"):
    c1, c2 = st.columns(2)
    with c1:
        completed_by = st.text_input("Completed By")
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        meet_with = st.text_input("Meet With")
    with c2:
        report_date = st.date_input("Date", value=date.today())
        machine = st.text_input("Machine")
        sc1, sc2 = st.columns(2)
        with sc1: m_type = st.text_input("Type")
        with sc2: serial_no = st.text_input("Serial No")

    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")
    
    st.divider()
    cs1, cs2 = st.columns(2)
    with cs1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=100, width=200, key="c_t")
    with cs2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=100, width=200, key="c_c")

    submitted = st.form_submit_button("Generate & Preview")

if submitted:
    if not completed_by: st.error("Isi Nama Teknisi!")
    else:
        # Proses Data
        final_list = [{'img': optimize_image(i['file']), 'caption': i['caption']} for i in photo_data]
        logo_img = Image.open(uploaded_logo) if uploaded_logo else None
        sig_t_img = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        sig_c_img = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
        
        report_data = {
            "Completed By": completed_by, "Customer": customer, "Machine": machine,
            "Date": str(report_date), "Meet With": meet_with, "Type": m_type,
            "Serial No": serial_no, "Problem": problem, "Follow Up": follow_up
        }
        
        st.session_state.update({'last_data': report_data, 'sig_t': sig_t_img, 'sig_c': sig_c_img, 'logo': logo_img, 'extra_items': final_list})
        st.success("Laporan Berhasil Dibuat!")

if 'last_data' in st.session_state:
    st.write("---")
    pdf_bytes = create_pdf(st.session_state['last_data'], st.session_state['sig_t'], st.session_state['sig_c'], logo=st.session_state.get('logo'), extra_items=st.session_state.get('extra_items'))
    
    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=f"Report_{st.session_state['last_data']['Serial No']}.pdf")
    
    # Backup Preview: Jika embed gagal, user tetap bisa download
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        st.markdown(f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf">', unsafe_allow_html=True)
    except:
        st.info("Gunakan tombol download di atas untuk melihat PDF.")
