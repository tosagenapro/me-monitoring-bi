import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px
import time
import io
import requests
from PIL import Image, ImageDraw

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP ME BI BPP", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. QR DETECTOR LOGIC ---
query_params = st.query_params
qr_code_detected = query_params.get("unit")
BASE_URL_APP = "https://simantap-bi-bpp.streamlit.app"

# --- 3. MASTER SOW DINAMIS ---
SOW_MASTER = {
    "AC": {
        "Harian": ["Suhu Ruangan (°C)", "Cek suara abnormal outdoor", "Cek kebocoran air indoor"],
        "Mingguan": ["Arus Motor Fan (Ampere)", "Pembersihan filter udara", "Cek kondisi remote"],
        "Bulanan": ["Tekanan Freon (Psi)", "Cuci evaporator", "Cek arus total (Ampere)"]
    },
    "AHU": {
        "Harian": ["Cek tekanan udara (Pa)", "Cek suara bearing motor", "Cek kondisi V-Belt"],
        "Mingguan": ["Pembersihan pre-filter", "Cek drain pan", "Arus motor (Ampere)"],
        "Bulanan": ["Cek motor damper", "Cleaning coil", "Inspeksi panel kontrol"]
    },
    "BAS": {
        "Harian": ["Cek koneksi controller", "Suhu monitoring pusat (°C)", "Log alarm aktif"],
        "Mingguan": ["Cek sensor kelembaban", "Fungsi jadwal otomatis", "Backup data log harian"],
        "Bulanan": ["Kalibrasi sensor suhu", "Update software controller", "Cek hardware server"]
    },
    "GENSET": {
        "Harian": ["Bahan Bakar (%)", "Level Oli", "Tegangan Baterai (Volt)"],
        "Mingguan": ["Suhu saat Running (°C)", "Uji pemanasan (Menit)", "Cek kebocoran"],
        "Bulanan": ["Tegangan Output (Volt)", "Frekuensi (Hz)", "Cek sistem proteksi"]
    },
    "UPS": {
        "Harian": ["Kapasitas Baterai (%)", "Tegangan Input (Volt) ", "Indikator Lampu"],
        "Mingguan": ["Tegangan Output (Volt)", "Suhu Battery Pack (°C)", "Cek Fan"],
        "Bulanan": ["Uji Discharge (Menit)", "Kekencangan terminal", "Laporan Load"]
    },
    "PANEL": {
        "Harian": ["Lampu indikator", "Suara dengung", "Suhu ruangan panel"],
        "Mingguan": ["Kekencangan baut", "Fungsi MCB", "Pembersihan debu"],
        "Bulanan": ["Pengukuran beban (Ampere)", "Cek grounding", "Thermography"]
    },
    "UMUM": {
        "Harian": ["Kebersihan unit", "Fungsi operasional"],
        "Mingguan": ["Pemeriksaan fisik"],
        "Bulanan": ["Catatan performa bulanan"]
    }
}

# --- 4. CSS CUSTOM & HEADER ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background: #0f172a; }
    .main-header { 
        text-align: center; padding: 25px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
        border-bottom: 3px solid #38bdf8; border-radius: 0 0 25px 25px; margin-bottom: 30px; 
    }
    .main-header h1 { color: #38bdf8; margin: 0; font-size: 1.8rem; font-weight: 800; letter-spacing: 1px; }
    .main-header p { color: #f8fafc; font-weight: 500; font-size: 1.1rem; margin: 12px 0 0 0; letter-spacing: 0.5px; }
    .stat-card { background: #1e293b; border-radius: 12px; padding: 15px; border-bottom: 3px solid #38bdf8; text-align: center; transition: 0.3s; }
    div.stButton > button { 
        width: 100%; height: 60px !important; background: #1e293b !important; border: 1px solid #334155 !important; 
        border-radius: 12px !important; color: #f8fafc !important; font-weight: bold !important; 
    }
    </style>
    <div class="main-header">
        <h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1>
        <p>Sistem Informasi Monitoring Aset dan Pemeliharaan Terpadu</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. FUNGSI ---
@st.cache_data(ttl=30)
def load_data():
    a = supabase.table("assets").select("*").order("nama_aset").limit(200).execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
staff_map = {s['nama']: s for s in staff_list}
opt_asset = {f"[{a['kode_qr']}] {a['nama_aset']}": a for a in assets_list}
qr_map = {a['kode_qr']: a for a in assets_list}

list_tek = [s['nama'] for s in staff_list if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_list if s['kategori'] == 'PEGAWAI']
list_kat_master = ["SEMUA", "AC", "AHU", "UPS", "BAS", "PANEL", "GENSET", "UMUM"]

def upload_foto(file):
    if file:
        try:
            # --- FITUR STAMP FOTO ---
            img = Image.open(file)
            draw = ImageDraw.Draw(img)
            waktu_st = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            teks_st = f"SIMANTAP ME | {waktu_st}"
            w, h = img.size
            draw.text((w - 280, h - 50), teks_st, fill=(255, 255, 255)) 
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            
            fname = f"{uuid.uuid4()}.jpg"
            supabase.storage.from_("foto_maintenance").upload(fname, img_byte_arr.getvalue(), {"content-type":"image/jpeg"})
            return f"{URL}/storage/v1/object/public/foto_maintenance/{fname}"
        except: return None
    return None

def generate_pdf_final(df, rentang, peg, tek, judul, tipe="Maintenance"):
    try:
        pdf = FPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"{judul} - KPwBI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10); pdf.cell(0, 7, f"Periode: {rentang}", ln=True, align="C"); pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 8); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        w = [60, 25, 30, 25, 130] if tipe=="Maintenance" else [60, 70, 30, 30, 80]
        cols = ["Nama Aset", "Periode", "Teknisi", "Kondisi", "Detail Pekerjaan"] if tipe=="Maintenance" else ["Nama Aset", "Masalah", "Pelapor", "Status", "Tindakan Perbaikan"]
        
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln(); pdf.set_font("Helvetica", "", 7); pdf.set_text_color(0, 0, 0)
        
        for _, row in df.iterrows():
            if tipe == "Maintenance":
                pdf.cell(w[0], 10, str(row.get('Nama Aset','')), 1); pdf.cell(w[1], 10, str(row.get('periode','')), 1)
                pdf.cell(w[2], 10, str(row.get('teknisi','')), 1); pdf.cell(w[3], 10, str(row.get('kondisi','')), 1)
                pdf.cell(w[4], 10, str(row.get('keterangan',''))[:95], 1); pdf.ln()
            else:
                pdf.cell(w[0], 10, str(row.get('Nama Aset','')), 1); pdf.cell(w[1], 10, str(row.get('masalah',''))[:50], 1)
                pdf.cell(w[2], 10, str(row.get('teknisi','')), 1); pdf.cell(w[3], 10, str(row.get('status','')), 1)
                pdf.cell(w[4], 10, str(row.get('tindakan_perbaikan',''))[:60], 1); pdf.ln()

        # Signature
        pdf.ln(10); pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, "Known,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
        pos_p = str(peg.get('posisi', '')).replace('"', '')
        pdf.cell(138, 5, pos_p, 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
        pdf.ln(18); pdf.set_font("Helvetica", "BU", 10) # Underline
        pdf.cell(138, 5, str(peg.get('nama', '')), 0, 0, "C"); pdf.cell(138, 5, str(tek.get('nama', '')), 0, 1, "C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, str(peg.get('jabatan_pdf', '')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# --- 6. ROUTING ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
if qr_code_detected and 'qr_handled' not in st.session_state:
    st.session_state.hal = 'LandingQR'; st.session_state.qr_handled = True

def pindah(n): st.session_state.hal = n; st.rerun()

# --- 7. HALAMAN UTAMA (LOGIC) ---
# ... (Sisa routing halaman tetap mengikuti struktur yang Bapak kirim sebelumnya)