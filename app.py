import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- KONFIGURASI FILE ---
EXCEL_FILE = "service_reports.xlsx"

class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img

    def header(self):
        if self.page_no() == 1:
            # Banner Biru Estetik
            self.set_fill_color(41, 128, 185) 
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 16)
            self.cell(0, 15, "  SERVICE REPORT  ", fill=True, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            # Logo diletakkan setelah banner agar tidak tertutup (posisi mengambang)
            if self.logo_img:
                # x=12, y=10 posisi di depan banner biru
                self.image(self.logo_img, x=12, y=10, h=10)
            
            self.set_text_color(0, 0, 0)
            self.ln(5)

def optimize_image(uploaded_file, max_res=(800, 800)):
    if uploaded_file is None: return None
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail(max_res, Image.Resampling.LANCZOS)
    return img

def save_to_excel(new_data):
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
        df.to_excel(EXCEL_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Error Excel: {e}")
        return False

# --- FUNGSI BUAT PDF (GRID 2x2 UNTUK FOTO) ---
def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    # --- INFO BOX ---
    pdf.set_font("helvetica", 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    
    # Baris 1: Technician & Customer
    pdf.cell(35, 8, " Technician", border=1, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['Completed By']}", border=1)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(35, 8, " Customer", border=1, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['Customer']}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Baris 2: Machine & Date
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(35, 8, " Machine", border=1, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['Machine']}", border=1)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(35, 8, " Date", border=1, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['Date']}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Baris 3: Meet With, Type & Serial No
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(35, 8, " Meet With", border=1, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.cell(60, 8, f" {data['Meet With']}", border=1)
    
    # Grid kecil untuk Type dan Serial No
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(15, 8, " Type", border=1, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.cell(25, 8, f" {data['Type']}", border=1)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(20, 8, " Ser No", border=1, fill=True)
    pdf.set_font("helvetica", '', 9)
    pdf.cell(35, 8, f" {data['Serial No']}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(8)
    
    # --- ISI LAPORAN ---
    pdf.set_draw_color(41, 128, 185)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 8, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['Problem'], border=0)
    pdf.ln(5)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 8, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['Follow Up'], border=0)

    # --- LAMPIRAN FOTO (GRID 2x2) ---
    if extra_items:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(0, 10, "DOCUMENTATION PHOTOS", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        
        # Pengaturan Grid
        col_width = 90
        row_height = 70
        margin = 10
        
        for i, item in enumerate(extra_items):
            # Tentukan posisi X dan Y berdasarkan indeks (0, 1, 2, 3)
            col = i % 2
            row = (i // 2) % 2
            
            # Jika sudah gambar ke-5, buat halaman baru
            if i > 0 and i % 4 == 0:
                pdf.add_page()
                pdf.set_font("helvetica", 'B', 12)
                pdf.cell(0, 10, "DOCUMENTATION PHOTOS (Cont.)", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(5)
            
            x_pos = margin + (col * (col_width + 10))
            # Hitung Y berdasarkan row saat ini di halaman
            y_start = 30 + (row * (row_height + 25))
            
            # Frame Foto
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x_pos, y_start, col_width, row_height)
            
            # Gambar (Fit to Box)
            pdf.image(item['img'], x=x_pos+2, y=y_start+2, w=col_width-4, h=row_height-10)
            
            # Keterangan di bawah foto
            pdf.set_xy(x_pos, y_start + row_height - 6)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(col_width, 5, f"Photo {i+1}: {item['caption'][:50]}", align='C')

    # --- TANDA TANGAN ---
    pdf.set_y(-60)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(95, 10, "Service Technician,", align='C')
    pdf.cell(95, 10, "Customer / PIC,", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    sig_y = pdf.get_y()
    if sig_t: pdf.image(sig_t, x=42, y=sig_y, w=25)
    if sig_c: pdf.image(sig_c, x=138, y=sig_y, w=25)
    
    pdf.set_y(sig_y + 20)
    pdf.set_font("helvetica", 'BU', 10)
    pdf.cell(95, 10, f"{data['Completed By']}", align='C')
    pdf.cell(95, 10, f"{data['Meet With']}", align='C')

    return bytes(pdf.output())

# --- UI STREAMLIT ---
st.set_page_config(page_title="Finpac Service Report", layout="centered")
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
        machine = st.text_input("Machine")
    with c2:
        report_date = st.date_input("Date", value=date.today())
        meet_with = st.text_input("Meet With")
        sc1, sc2 = st.columns(2)
        with sc1: m_type = st.text_input("Type")
        with sc2: serial_no = st.text_input("Serial No")

    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")
    
    st.divider()
    cs1, cs2 = st.columns(2)
    with cs1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=120, width=250, key="c_t")
    with cs2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=120, width=250, key="c_c")

    submitted = st.form_submit_button("Simpan & Lihat Preview")

if submitted:
    if not completed_by: st.error("Lengkapi data!")
    else:
        final_list = [{'img': optimize_image(i['file']), 'caption': i['caption']} for i in photo_data]
        logo_img = optimize_image(uploaded_logo, (300, 300))
        sig_t_img = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        sig_c_img = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
        
        report_data = {
            "Completed By": completed_by, "Customer": customer, "Machine": machine,
            "Date": str(report_date), "Meet With": meet_with, "Type": m_type,
            "Serial No": serial_no, "Problem": problem, "Follow Up": follow_up
        }
        
        if save_to_excel(report_data):
            st.session_state.update({'last_data': report_data, 'sig_t': sig_t_img, 'sig_c': sig_c_img, 'logo': logo_img, 'extra_items': final_list})
            st.success("Data Tersimpan!")

if 'last_data' in st.session_state:
    st.write("---")
    st.subheader("🔍 PDF Preview")
    pdf_bytes = create_pdf(st.session_state['last_data'], st.session_state['sig_t'], st.session_state['sig_c'], logo=st.session_state.get('logo'), extra_items=st.session_state.get('extra_items'))
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    st.markdown(f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">', unsafe_allow_html=True)
    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=f"Report_{st.session_state['last_data']['Serial No']}.pdf")
