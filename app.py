import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# 1. KONFIGURASI
EXCEL_FILE = "service_reports.xlsx"

# 2. DEFINISI KELAS PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'SERVICE REPORT', 1, 1, 'C')
        self.ln(5)

# 3. FUNGSI PENYIMPANAN EXCEL
def save_to_excel(new_data):
    try:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
        df.to_excel(EXCEL_FILE, index=False)
        return True
    except PermissionError:
        st.error(f"⚠️ Tutup file '{EXCEL_FILE}' di Excel terlebih dahulu!")
        return False
    except Exception as e:
        st.error(f"Terjadi kesalahan saat menyimpan Excel: {e}")
        return False

# 4. FUNGSI PEMBUATAN PDF
def create_pdf(data, sig_t=None, sig_c=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Tabel Informasi Utama[cite: 1]
    pdf.cell(100, 10, f"Customer: {data['Customer']}", border=1)
    pdf.cell(90, 10, f"Report No: {data['No']}", border=1, ln=1)
    pdf.cell(100, 10, f"Machine Type: {data['Machine Type']}", border=1)
    pdf.cell(90, 10, f"Date: {data['Date']}", border=1, ln=1)
    pdf.cell(100, 10, f"Meet With: {data['Meet With']}", border=1)
    pdf.cell(90, 10, f"Completed By: {data['Completed By']}", border=1, ln=1)
    
    pdf.ln(5)
    
    # Detail Masalah & Tindakan[cite: 1]
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Problem Description:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Problem'], border=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, "Report / Follow Up Action:", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, data['Follow Up'], border=1)
    
    pdf.ln(10)
    
    # Bagian Tanda Tangan[cite: 1]
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(90, 10, "Technician,", align='C')
    pdf.cell(90, 10, "Customer,", ln=1, align='C')
    
    # Posisi Y untuk gambar tanda tangan[cite: 1]
    sig_y_pos = pdf.get_y()
    
    if sig_t:
        # fpdf2 mendukung langsung objek PIL Image[cite: 1]
        pdf.image(sig_t, x=40, y=sig_y_pos, w=30)
        
    if sig_c:
        pdf.image(sig_c, x=140, y=sig_y_pos, w=30)
    
    pdf.ln(25) # Ruang untuk tanda tangan
    
    # Nama Terang[cite: 1]
    pdf.set_font("Arial", size=10)
    pdf.cell(90, 10, f"( {data['Completed By']} )", align='C')
    pdf.cell(90, 10, f"( {data['Meet With']} )", ln=1, align='C')

    return pdf.output()

# 5. TAMPILAN UTAMA (UI)[cite: 1]
st.set_page_config(page_title="Service Report Digital", layout="centered")
st.title("Digital Service Report")
st.write("Laporan servis untuk maintenance mesin Kilian & Romaco.")

with st.form("service_form"):
    col1, col2 = st.columns(2)
    with col1:
        report_no = st.text_input("Service Report No")
        completed_by = st.text_input("Completed By (Teknisi)")
        report_date = st.date_input("Date", value=date.today())
    with col2:
        customer = st.text_input("Customer", value="PT. Finpac Anugerah Indonesia")
        machine_type = st.text_input("Machine Type (e.g. Kilian Press)")
        meet_with = st.text_input("Meet With (PIC Customer)")

    problem = st.text_area("Problem Description")
    follow_up = st.text_area("Report / Follow Up Action")
    
    st.divider()
    
    # Area Tanda Tangan Digital[cite: 1]
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.write("Tanda Tangan Teknisi:")
        c_tech = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, key="tech")
    with col_sig2:
        st.write("Tanda Tangan Customer:")
        c_cust = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, key="cust")

    submitted = st.form_submit_button("Simpan & Generate Report")

# 6. LOGIKA SETELAH SUBMIT[cite: 1]
if submitted:
    if not report_no or not completed_by:
        st.error("Nomor Report dan Nama Teknisi wajib diisi!")
    else:
        # Konversi data canvas ke format gambar Pillow[cite: 1]
        img_t = Image.fromarray(c_tech.image_data.astype('uint8'), 'RGBA') if c_tech.image_data is not None else None
        img_c = Image.fromarray(c_cust.image_data.astype('uint8'), 'RGBA') if c_cust.image_data is not None else None
            
        data_to_save = {
            "No": report_no, "Completed By": completed_by, "Date": str(report_date),
            "Customer": customer, "Meet With": meet_with, "Machine Type": machine_type,
            "Problem": problem, "Follow Up": follow_up
        }
        
        if save_to_excel(data_to_save):
            st.session_state['report_ready'] = data_to_save
            st.session_state['sig_t'] = img_t
            st.session_state['sig_c'] = img_c
            st.success("Laporan berhasil disimpan ke Excel!")

# 7. OPSI DOWNLOAD PDF[cite: 1]
if 'report_ready' in st.session_state:
    st.divider()
    try:
        final_pdf = create_pdf(
            st.session_state['report_ready'], 
            st.session_state['sig_t'], 
            st.session_state['sig_c']
        )
        st.download_button(
            label="⬇️ Download PDF Service Report",
            data=final_pdf,
            file_name=f"Report_{st.session_state['report_ready']['No']}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Gagal membuat PDF: {e}")
