import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF, XPos, YPos
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

class PDF(FPDF):
    def __init__(self, logo_img=None):
        super().__init__()
        self.logo_img = logo_img
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.page_no() == 1:
            if self.logo_img:
                logo_h = 25 
                w_orig, h_orig = self.logo_img.size
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

def create_pdf(data, sig_t=None, sig_c=None, logo=None, extra_items=None):
    pdf = PDF(logo_img=logo)
    pdf.add_page()
    
    # --- INFO BOX ---
    pdf.set_font("helvetica", 'B', 8)
    pdf.set_fill_color(240, 240, 240)
    h_row = 7
    
    pdf.cell(30, h_row, " Technician", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data['Completed By']}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(30, h_row, " Customer", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data['Customer']}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.cell(30, h_row, " Meet With", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data['Meet With']}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(30, h_row, " Date", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data['Date']}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.cell(30, h_row, " Machine", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(65, h_row, f" {data['Machine']}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(15, h_row, " Type", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(30, h_row, f" {data['Type']}", border=1)
    pdf.set_font("helvetica", 'B', 8)
    pdf.cell(20, h_row, " Ser No", border=1, fill=True)
    pdf.set_font("helvetica", '', 8)
    pdf.cell(30, h_row, f" {data['Serial No']}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(4)
    
    # --- ISI LAPORAN ---
    pdf.set_draw_color(41, 128, 185)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, data['Problem'], border=0)
    pdf.ln(3)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "REPORT / FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("helvetica", '', 9)
    pdf.multi_cell(0, 5, data['Follow Up'], border=0)
    pdf.ln(5)

    # --- LAMPIRAN FOTO (Jika Ada) ---
    if extra_items:
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 12)
        pdf.cell(0, 10, "DOCUMENTATION PHOTOS", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        cw, rh, gap = 90, 70, 10
        for i, item in enumerate(extra_items):
            if i > 0 and i % 4 == 0:
                pdf.add_page()
            col, row = i % 2, (i // 2) % 2
            x, y = 10 + (col * (cw + gap)), 30 + (row * (rh + 15))
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x, y, cw, rh)
            pdf.image(item['img'], x=x+2, y=y+2, w=cw-4, h=rh-10)
            pdf.set_xy(x, y + rh - 6)
            pdf.set_font("helvetica", 'I', 7)
            pdf.cell(cw, 5, f"Photo {i+1}: {item['caption'][:50]}", align='C')
        pdf.ln(10) # Beri jarak setelah foto terakhir

    # --- TANDA TANGAN (Selalu di Halaman Terakhir) ---
    # Cek sisa ruang, jika sangat sempit, pindah halaman
    if pdf.get_y() > 240:
        pdf.add_page()
    
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 9)
    pdf.cell(95, 7, "Service Technician,", align='C')
    pdf.cell(95, 7, "Customer / PIC,", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    sig_y_pos = pdf.get_y()
    if sig_t: pdf.image(sig_t, x=42, y=sig_y_pos, w=25)
    if sig_c: pdf.image(sig_c, x=138, y=sig_y_pos, w=25)
    
    pdf.ln(20)
    pdf.set_font("helvetica", 'BU', 9)
    pdf.cell(95, 7, f"{data['Completed By']}", align='C')
    pdf.cell(95, 7, f"{data['Meet With']}", align='C')

    return bytes(pdf.output())

# --- UI STREAMLIT TETAP SAMA ---
