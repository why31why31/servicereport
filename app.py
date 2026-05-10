import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- 1. UTILS ---
def clean_text(text):
    if not text: return ""
    replacements = {'\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2022': '*', '\xb0': ' deg '}
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def optimize_image(uploaded_file, max_res=(600, 600)):
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
        # Mengurangi margin bawah agar tanda tangan tidak mudah pindah halaman
        self.set_auto_page_break(auto=True, margin=10)

    def header(self):
        if self.page_no() == 1:
            if self.logo_img:
                w_orig, h_orig = self.logo_img.size
                logo_h = 20
                logo_w = (w_orig / h_orig) * logo_h
                self.image(self.logo_img, x=(210 - logo_w) / 2, y=8, h=logo_h)
                self.ln(logo_h + 2)
            self.set_fill_color(41, 128, 185)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(2)

# --- 3. GENERATION FUNCTION ---
def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    # --- INFO BOX ---
    pdf.set_font("helvetica", 'B', 8)
    pdf.set_fill_color(240, 240, 240)
    h_row = 6.5 # Memperkecil tinggi baris
    d = {k: clean_text(str(v)) for k, v in data.items()}

    pdf.cell(30, h_row, " Technician", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Completed By')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Customer", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Customer')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Meet With", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Meet With')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Date", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Date')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", 'B', 8); pdf.cell(30, h_row, " Machine", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(65, h_row, f" {d.get('Machine')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(15, h_row, " Type", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(30, h_row, f" {d.get('Type')}", border=1)
    pdf.set_font("helvetica", 'B', 8); pdf.cell(20, h_row, " Ser No", border=1, fill=True)
    pdf.set_font("helvetica", '', 8); pdf.cell(30, h_row, f" {d.get('Serial No')}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(3)
    
    # --- CONTENT ---
    pdf.set_draw_color(41, 128, 185)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 6, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, d.get('Problem'), border=0)
    pdf.ln(2)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 6, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, d.get('Follow Up'), border=0)
    pdf.ln(3)

    # --- CENTERED IMAGE GRID (2x2) ---
    if extra_items:
        # Pindah halaman hanya jika sisa ruang benar-benar habis
        if pdf.get_y() > 250: pdf.add_page()
        
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 6, "DOCUMENTATION PHOTOS", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        
        cw, rh = 85, 58 # Mengurangi sedikit tinggi foto (dari 60 ke 58)
        gap = 10
        margin_left = (210 - (cw * 2 + gap)) / 2
        
        start_y = pdf.get_y()
        
        for i, item in enumerate(extra_items):
            if i > 0 and i % 4 == 0:
                pdf.add_page()
                start_y = pdf.get_y() + 5
            
            col = i % 2
            row = (i // 2) % 2
            
            x_pos = margin_left + (col * (cw + gap))
            y_pos = start_y + (row * (rh + 10))
            
            # Deteksi Page Break saat render foto
            if y_pos + rh > 280:
                pdf.add_page()
                start_y = pdf.get_y() + 5
                y_pos = start_y

            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x_pos, y_pos, cw, rh)
            pdf.image(item['img'], x=x_pos+1, y=y_pos+1, w=cw-2, h=rh-8)
            
            pdf.set_xy(x_pos, y_pos + rh - 6)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(cw, 5, f"Photo {i+1}: {clean_text(item['caption'][:40])}", align='C')
            
            if col == 1 or i == len(extra_items)-1:
                pdf.set_y(y_pos + rh + 5)

    # --- SIGNATURES ---
    # Jika sisa ruang < 35mm, baru pindah halaman
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

# --- 4. STREAMLIT UI (TETAP SAMA) ---
