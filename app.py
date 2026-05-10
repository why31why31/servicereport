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
            if self.logo_img:
                self.image(self.logo_img, x=10, y=8, w=30)
            
            # Judul Laporan dengan Style Estetik (Biru Tua)
            self.set_fill_color(41, 128, 185) 
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 16)
            self.cell(0, 15, "  SERVICE REPORT  ", fill=True, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(5)

# --- FUNGSI OPTIMASI GAMBAR ---
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

# --- FUNGSI BUAT PDF ESTETIK ---
def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None, img_width_adj=100):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    # --- INFO BOX MODERN ---
    pdf.set_font("helvetica", 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    
    # Grid Data
    fields = [
        ("Technician", data['Completed By'], "Customer", data['Customer']),
        ("Machine", data['Machine'], "Date", data['Date']),
        ("Meet With", data['Meet With'], "Serial No", data['Serial No'])
    ]
    
    for label1, val1, label2, val2 in fields:
        pdf.set_font("helvetica", 'B', 9)
        pdf.cell(35, 8, f" {label1}", border=1, fill=True)
        pdf.set_font("helvetica", '', 9)
        pdf.cell(60, 8, f" {val1}", border=1)
        pdf.set_font("helvetica", 'B', 9)
        pdf.cell(35, 8, f" {label2}", border=1, fill=True)
        pdf.set_font("helvetica", '', 9)
        pdf.cell(60, 8, f" {val2}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(8)
    
    # --- SEKSI ISI LAPORAN ---
    pdf.set_draw_color(41, 128, 185)
    
    # Problem Description
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 8, "PROBLEM DESCRIPTION", b='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['Problem'], border=0)
    pdf.ln(5)
    
    # Follow Up Action
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 8, "REPORT / FOLLOW UP ACTION", b='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, data['Follow Up'], border=0)

    # --- LAMPIRAN FOTO ---
    if extra_items:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(0, 10, "DOCUMENTATION PHOTOS", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        
        for i, item in enumerate(extra_items):
            w_orig, h_orig = item['img'].size
            img_w = img_width_adj 
            img_h = (h_orig / w_orig) * img_w
            
            if pdf.get_y() + img_h > 240: pdf.add_page()
            
            x_pos = (210 - img_w) / 2
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x_pos - 1, pdf.get_y() - 1, img_w + 2, img_h + 8) # Frame
            
            pdf.image(item['img'], x=x_pos, y=pdf.get_y(), w=img_w)
            pdf.set_y(pdf.get_y() + img_h + 1)
            pdf.set_font("helvetica", 'I', 8)
            pdf.cell(0, 6, f"Photo {i+1}: {item['caption']}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(8)

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
uploaded_photos = st.sidebar.file_uploader("Pilih Foto Lampiran", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

photo_data = []
if uploaded_photos:
    st.sidebar.subheader("Keterangan Lampiran")
    for i, p in enumerate(uploaded_photos):
        cap = st.sidebar.text_input(f"Ket Foto {i+1}", key=f"cap_{i}")
        photo_data.append({'file': p, 'caption': cap})

img_adj = st.sidebar.slider("Lebar Foto di PDF (mm)", 30, 180, 100)

with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        completed_by = st.text_input("Completed By")
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine = st.text_input("Machine")
    with col2:
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
        st.write("Teknisi:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=120, width=250, key="c_t")
    with cs2:
        st.write("Customer:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="rgba(0,0,0,0)", height=120, width=250, key="c_c")

    submitted = st.form_submit_button("Simpan & Lihat Preview")

if submitted:
    if not completed_by: st.error("Isi Nama Teknisi!")
    else:
        # Optimasi Data
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
            st.session_state.update({'last_data': report_data, 'sig_t': sig_t_img, 'sig_c': sig_c_img, 'logo': logo_img, 'extra_items': final_list, 'img_adj': img_adj})
            st.success("Tersimpan!")

# --- PREVIEW (STABIL) ---
if 'last_data' in st.session_state:
    st.write("---")
    st.subheader("🔍 PDF Live Preview")
    pdf_bytes = create_pdf(st.session_state['last_data'], st.session_state['sig_t'], st.session_state['sig_c'], logo=st.session_state.get('logo'), extra_items=st.session_state.get('extra_items'), img_width_adj=st.session_state.get('img_adj', 100))
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    # Menggunakan embed agar tidak diblokir Chrome
    st.markdown(f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">', unsafe_allow_html=True)
    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=f"Report_{st.session_state['last_data']['Serial No']}.pdf")
