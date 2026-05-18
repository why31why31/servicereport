import streamlit as st
import pandas as pd
from datetime import datetime, date
from fpdf import FPDF, XPos, YPos
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. USER ACCESS CONFIG ---
USER_CREDENTIALS = {
    "Asep": "as1234",
    "Rangga": "rangga123",
    "Wahyu": "wahyu123",
    "Ali": "ali123",
    "Karim": "karim123",
    "admin": "service123"
}

# --- INISIALISASI DRAFT INDEPENDEN (TERMASUK BLOK CANVAS) ---
if "saved_draft" not in st.session_state:
    st.session_state["saved_draft"] = {
        "cb": "", "cu": "", "mw": "", "status": "Open",
        "rd": date.today(), "ma": "Siebler", "ty": "", "sn": "",
        "pr": "", "fu": "",
        "t_sig_raw": None,  # Draft tanda tangan teknisi (JSON)
        "c_sig_raw": None   # Draft tanda tangan customer (JSON)
    }

def login_screen():
    st.title("🔐 Finpac Service Portal")
    st.write("Please sign in to continue")
    with st.form("login_form"):
        user = st.text_input("Username", key="login_user")
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.form_submit_button("Sign In", use_container_width=True):
            if user in USER_CREDENTIALS and USER_CREDENTIALS[user] == pw:
                st.session_state["authenticated"] = True
                st.session_state["user_profile"] = user
                st.rerun()
            else:
                st.error("Invalid Username or Password")

# --- 2. GOOGLE SHEETS CONFIG ---
SPREADSHEET_ID = "1g7P6Xkm-G6JE1UR1GLOJ63HISknqdlH21viT2JoC4PY"
WORKSHEET_NAME = "Daily Report Technic New (2026)"

def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            return gspread.authorize(creds)
    except Exception as e:
        return None

# --- UTILS: UNICODE TEXT CLEANER ---
def clean_text(text):
    if not text: 
        return ""
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u201c': '"', '\u201d': '"',
        '\u2018': "'", '\u2019': "'", '\xb0': ' deg ', '\xb1': '+/-', '\xb5': 'u',
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- 3. PDF ENGINE ---
class PDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path
        self.set_margin(15)

    def header(self):
        if self.page_no() == 1:
            if self.logo_path and os.path.exists(self.logo_path):
                self.image(self.logo_path, x=70, y=8, w=70)
                self.set_y(28)
            else:
                self.set_y(10)
            self.set_fill_color(41, 128, 185)
            self.set_text_color(255, 255, 255)
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, "SERVICE REPORT", fill=True, align='C', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
            self.ln(2)

def create_pdf(data, s_t, s_c, logo_path, photos):
    pdf = PDF(logo_path=logo_path)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    pdf.set_font("helvetica", 'B', 9); pdf.set_fill_color(245, 245, 245)
    fields = [
        [("Technician", clean_text(data['cb'])), ("Date", clean_text(data['rd']))],
        [("Customer", clean_text(data['cu'])), ("Meet with", clean_text(data['mw']))],
        [("Machine", clean_text(data['ma'])), ("Type", clean_text(data['ty'])), ("S/N", clean_text(data['sn']))]
    ]
    for row in fields:
        for label, value in row:
            pdf.set_font("helvetica", 'B', 9); pdf.cell(25, 7, f" {label}:", fill=True)
            pdf.set_font("helvetica", '', 9); pdf.cell(65 if len(row)==2 else 35, 7, f" {value}", border='B')
        pdf.ln(9)
    
    pdf.ln(2); pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 7, "PROBLEM DESCRIPTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, clean_text(data['pr']))
    pdf.ln(3)
    
    pdf.cell(0, 7, "FOLLOW UP ACTION", border='B', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", '', 10)
    pdf.multi_cell(0, 6, clean_text(data['fu']))

    if photos:
        if pdf.get_y() > 180: pdf.add_page()
        pdf.ln(5); pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 8, "ATTACHMENTS", border='B', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(4)
        img_w, img_h = 85, 60
        y_fix = pdf.get_y()
        for i, p in enumerate(photos):
            col = i % 2
            if col == 0 and (y_fix + img_h + 10) > 275:
                pdf.add_page(); y_fix = pdf.get_y() + 5
            x_pos = 15 if col == 0 else 110
            pdf.rect(x_pos, y_fix, img_w, img_h)
            pdf.image(p['img'], x=x_pos+1, y=y_fix+1, w=img_w-2, h=img_h-10)
            pdf.set_xy(x_pos, y_fix + img_h - 7); pdf.set_font("helvetica", 'I', 8)
            pdf.cell(img_w, 5, f"Photo {i+1}: {clean_text(p['cap'])}", align='C')
            if col == 1 or i == len(photos)-1:
                y_fix += (img_h + 8); pdf.set_y(y_fix)

    if pdf.get_y() > 220: pdf.add_page()
    pdf.ln(10); curr_y = pdf.get_y()
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(90, 7, "Service Technician,", align='C')
    pdf.cell(90, 7, "Customer,", align='C')
    if s_t: pdf.image(s_t, x=45, y=curr_y + 8, w=30)
    if s_c: pdf.image(s_c, x=135, y=curr_y + 8, w=30)
    pdf.set_y(curr_y + 20); pdf.set_font("helvetica", 'BU', 10)
    pdf.cell(90, 7, clean_text(data['cb']), align='C'); pdf.cell(90, 7, clean_text(data['mw']), align='C')
    return bytes(pdf.output())

# --- 4. MAIN APPLICATION ---
if "authenticated" not in st.session_state:
    st.set_page_config(page_title="Login - Service Report", layout="centered")
    login_screen()
else:
    st.set_page_config(page_title="Finpac Service Report", layout="centered")
    st.markdown("<style>iframe{border:1px solid #ddd !important; border-radius:10px; background-color:white;}</style>", unsafe_allow_html=True)

    # Callback pelacak teks formulir
    def track_change(field_key, widget_key):
        st.session_state["saved_draft"][field_key] = st.session_state[widget_key]

    # Sidebar Menu
    with st.sidebar:
        st.header("App Menu")
        current_user = st.session_state.get('user_profile', 'User')
        st.write(f"User: **{current_user}**")
        
        # TOMBOL RESET DRAFT MANUAL
        if st.button("🗑️ Reset Draft Data", use_container_width=True):
            st.session_state["saved_draft"] = {
                "cb": "", "cu": "", "mw": "", "status": "Open",
                "rd": date.today(), "ma": "Siebler", "ty": "", "sn": "",
                "pr": "", "fu": "",
                "t_sig_raw": None, "c_sig_raw": None
            }
            if 'final_pdf' in st.session_state: del st.session_state['final_pdf']
            st.rerun()

        # TOMBOL LOGOUT AMAN
        if st.button("🚪 Logout (Keep Draft)", type="secondary", use_container_width=True):
            if "authenticated" in st.session_state: del st.session_state["authenticated"]
            if "user_profile" in st.session_state: del st.session_state["user_profile"]
            st.rerun()
        
        st.write("---")
        st.header("Media Attachments")
        photo_files = st.file_uploader("Upload Photos", type=["jpg", "png"], accept_multiple_files=True, key="main_photo_uploader")
        caps = [st.text_input(f"Caption {i+1}", key=f"cap_input_{i}") for i in range(len(photo_files))]

    st.title("Digital Service Report")
    st.info("💡 **Draft System Active:** Ketikan dan Tanda Tangan Anda tersimpan otomatis meskipun Anda Logout.")
    client = get_gspread_client()

    draft = st.session_state["saved_draft"]

    # Render kolom input data
    col1, col2 = st.columns(2)
    with col1:
        cb = st.text_input("Technician Name", value=draft["cb"], key="w_cb", on_change=track_change, args=("cb", "w_cb"))
        cu = st.text_input("Customer Name", value=draft["cu"], key="w_cu", on_change=track_change, args=("cu", "w_cu"))
        mw = st.text_input("Meet With", value=draft["mw"], key="w_mw", on_change=track_change, args=("mw", "w_mw"))
        status_options = ["Open", "Pending", "Closed"]
        status = st.selectbox("Status", status_options, index=status_options.index(draft["status"]), key="w_status", on_change=track_change, args=("status", "w_status"))
    with col2:
        rd = st.date_input("Date", value=draft["rd"], key="w_rd", on_change=track_change, args=("rd", "w_rd"))
        machine_options = ["Siebler", "Noack", "Kilian", "Promatic", "Truking", "MG2", "FrymaKoruma", "Stephan", "Frewitt", "Lytzen", "Other Machine"]
        ma = st.selectbox("Machine", machine_options, index=machine_options.index(draft["ma"]), key="w_ma", on_change=track_change, args=("ma", "w_ma"))
        ty = st.text_input("Machine Type", value=draft["ty"], key="w_ty", on_change=track_change, args=("ty", "w_ty"))
        sn = st.text_input("Serial No", value=draft["sn"], key="w_sn", on_change=track_change, args=("sn", "w_sn"))
        
    pr = st.text_area("Problem Description", value=draft["pr"], key="w_pr", on_change=track_change, args=("pr", "w_pr"))
    fu = st.text_area("Action Taken / Follow Up", value=draft["fu"], key="w_fu", on_change=track_change, args=("fu", "w_fu"))

    st.write("---")
    st.write("### Signatures")
    sig_col1, sig_col2 = st.columns(2)
    
    with sig_col1:
        st.caption("Technician Signature")
        # Menggunakan .get() untuk mencegah KeyError secara permanen
        initial_t_sig = draft.get("t_sig_raw") if isinstance(draft, dict) else None
        
        can_t = st_canvas(
            stroke_width=2, height=150, width=330, key="t_sig", 
            background_color="white", update_streamlit=True,
            initial_drawing=initial_t_sig if initial_t_sig else None
        )
        # Amankan goresan baru ke draft secara real-time
        if can_t.json_data is not None and can_t.json_data.get("objects"):
            st.session_state["saved_draft"]["t_sig_raw"] = can_t.json_data

    with sig_col2:
        st.caption("Customer Signature")
        # Menggunakan .get() untuk mencegah KeyError secara permanen
        initial_c_sig = draft.get("c_sig_raw") if isinstance(draft, dict) else None
        
        can_c = st_canvas(
            stroke_width=2, height=150, width=330, key="c_sig", 
            background_color="white", update_streamlit=True,
            initial_drawing=initial_c_sig if initial_c_sig else None
        )
        # Amankan goresan baru ke draft secara real-time
        if can_c.json_data is not None and can_c.json_data.get("objects"):
            st.session_state["saved_draft"]["c_sig_raw"] = can_c.json_data
    with sig_col2:
        st.caption("Customer Signature")
        can_c = st_canvas(
            stroke_width=2, height=150, width=330, key="c_sig", 
            background_color="white", update_streamlit=True,
            initial_drawing=draft["c_sig_raw"] if draft["c_sig_raw"] else None
        )
        # Amankan goresan baru ke draft secara real-time
        if can_c.json_data is not None and can_c.json_data["objects"]:
            st.session_state["saved_draft"]["c_sig_raw"] = can_c.json_data

    st.write("---")
    if st.button("🚀 GENERATE PDF REPORT", type="primary", use_container_width=True):
        if not cb:
            st.error("Technician Name is required before generating report!")
        else:
            logo_path = "logo.png" 
            report_photos = []
            for i, pf in enumerate(photo_files):
                img = Image.open(pf)
                img.thumbnail((800, 800))
                report_photos.append({'img': img, 'cap': caps[i]})
            
            s_t = Image.fromarray(can_t.image_data.astype('uint8')) if (can_t.image_data is not None and len(can_t.json_data["objects"]) > 0) else None
            s_c = Image.fromarray(can_c.image_data.astype('uint8')) if (can_c.image_data is not None and len(can_c.json_data["objects"]) > 0) else None
            
            bundle = {'cb': cb, 'cu': cu, 'mw': mw, 'rd': str(rd), 'ma': ma, 'ty': ty, 'sn': sn, 'pr': pr, 'fu': fu}
            st.session_state['final_pdf'] = create_pdf(bundle, s_t, s_c, logo_path, report_photos)
            
            st.session_state['row_data'] = [str(rd), rd.strftime("%A"), cu, ma, ty, sn, pr, fu, cb, status]
            st.session_state['pdf_filename'] = f"Report_{cu}_{rd}.pdf"
            st.success("PDF Generated Successfully!")

    if 'final_pdf' in st.session_state:
        st.write("---")
        st.download_button("📥 DOWNLOAD PDF", data=st.session_state['final_pdf'], file_name=st.session_state['pdf_filename'], use_container_width=True)
        g_link = st.text_input("Paste GDrive Link here:")
        
        if st.button("💾 SAVE TO SPREADSHEET & RESET", use_container_width=True):
            if not g_link:
                st.warning("Please paste the GDrive link first.")
            elif client:
                try:
                    spreadsheet = client.open_by_key(SPREADSHEET_ID)
                    sheet = spreadsheet.worksheet(WORKSHEET_NAME)
                    hyperlink_formula = f'=HYPERLINK("{g_link}";"{st.session_state["pdf_filename"]}")'
                    full_row = st.session_state['row_data'] + [hyperlink_formula]
                    sheet.append_row(full_row, value_input_option='USER_ENTERED')
                    sheet.sort((1, 'asc'), range='A2:K5000')
                    st.success("Data Saved!")
                    
                    # Reset data teks dan hilangkan coretan tanda tangan setelah berhasil submit
                    st.session_state["saved_draft"] = {
                        "cb": "", "cu": "", "mw": "", "status": "Open",
                        "rd": date.today(), "ma": "Siebler", "ty": "", "sn": "",
                        "pr": "", "fu": "" ,
                        "t_sig_raw": None, "c_sig_raw": None
                    }
                    for k in ["final_pdf", "row_data", "pdf_filename"]:
                        if k in st.session_state: del st.session_state[k]
                    st.rerun()
                except Exception as e:
                    st.error(f"Spreadsheet Error: {e}")
