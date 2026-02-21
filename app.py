import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px
import time
from PIL import Image, ImageDraw
import io
import requests

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP ME BI BPP", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. QR DETECTOR LOGIC ---
query_params = st.query_params
qr_code_detected = query_params.get("unit")
BASE_URL_APP = "https://simantap-bi-bpp.streamlit.app"

# --- 3. MASTER SOW ---
SOW_MASTER = {
    "AC": {"Harian": ["Suhu Ruangan (°C)", "Cek suara abnormal outdoor", "Cek kebocoran air indoor"], "Mingguan": ["Arus Motor Fan (Ampere)", "Pembersihan filter udara", "Cek kondisi remote"], "Bulanan": ["Tekanan Freon (Psi)", "Cuci evaporator", "Cek arus total (Ampere)"]},
    "AHU": {"Harian": ["Cek tekanan udara (Pa)", "Cek suara bearing motor", "Cek kondisi V-Belt"], "Mingguan": ["Pembersihan pre-filter", "Cek drain pan", "Arus motor (Ampere)"], "Bulanan": ["Cek motor damper", "Cleaning coil", "Inspeksi panel kontrol"]},
    "UPS": {"Harian": ["Kapasitas Baterai (%)", "Tegangan Input (Volt)", "Indikator Lampu"], "Mingguan": ["Tegangan Output (Volt)", "Suhu Battery Pack (°C)", "Cek Fan"], "Bulanan": ["Uji Discharge (Menit)", "Kekencangan terminal", "Laporan Load"]},
    "GENSET": {"Harian": ["Bahan Bakar (%)", "Level Oli", "Tegangan Baterai (Volt)"], "Mingguan": ["Suhu saat Running (°C)", "Uji pemanasan (Menit)", "Cek kebocoran"], "Bulanan": ["Tegangan Output (Volt)", "Frekuensi (Hz)", "Cek sistem proteksi"]},
    "PANEL": {"Harian": ["Lampu indikator", "Suara dengung", "Suhu ruangan panel"], "Mingguan": ["Kekencangan baut", "Fungsi MCB", "Pembersihan debu"], "Bulanan": ["Pengukuran beban (Ampere)", "Cek grounding", "Thermography"]},
    "UMUM": {"Harian": ["Kebersihan unit", "Fungsi operasional"], "Mingguan": ["Pemeriksaan fisik"], "Bulanan": ["Catatan performa bulanan"]}
}

# --- 4. CSS CUSTOM ---
st.markdown("""<style>
    .stApp { background: #0f172a; }
    .main-header { text-align: center; padding: 20px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 3px solid #38bdf8; border-radius: 0 0 20px 20px; margin-bottom: 20px; }
    .main-header h1 { color: #38bdf8; margin: 0; font-size: 1.6rem; font-weight: 800; }
    div.stButton > button { width: 100%; height: 55px; background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 12px; color: #f8fafc; font-weight: bold; }
    div.stButton > button:hover { border-color: #38bdf8 !important; color: #38bdf8 !important; }
</style>""", unsafe_allow_html=True)

# --- 5. FUNGSI INTI ---
@st.cache_data(ttl=30)
def load_data():
    a = supabase.table("assets").select("*").order("nama_aset").execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
staff_map = {s['nama']: s for s in staff_list}
opt_asset = {f"[{a['kode_qr']}] {a['nama_aset']}": a for a in assets_list}
qr_map = {a['kode_qr']: a for a in assets_list}

def upload_foto(file):
    if file:
        img = Image.open(file).convert('RGB')
        img.thumbnail((800, 800))
        draw = ImageDraw.Draw(img)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text((10, 10), ts, fill="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        fname = f"{uuid.uuid4()}.jpg"
        supabase.storage.from_("foto_maintenance").upload(fname, buf.getvalue(), {"content-type":"image/jpeg"})
        url = supabase.storage.from_("foto_maintenance").get_public_url(fname)
        return url.replace("public/public", "public")
    return None

def generate_pdf_paripurna(df, rentang, peg, tek, judul, tipe="Maintenance"):
    try:
        pdf = FPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"{judul} - KPwBI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10); pdf.cell(0, 7, f"Periode: {rentang}", ln=True, align="C"); pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 8); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        w = [60, 30, 30, 30, 120] if tipe == "Maintenance" else [50, 60, 30, 30, 100]
        cols = ["Nama Aset", "Periode", "Teknisi", "Kondisi", "Detail Pekerjaan"] if tipe == "Maintenance" else ["Nama Aset", "Masalah", "Pelapor", "Status", "Tindakan Perbaikan"]
        
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln(); pdf.set_font("Helvetica", "", 7); pdf.set_text_color(0, 0, 0)
        
        for _, r in df.iterrows():
            pdf.cell(w[0], 10, str(r.get('Nama Aset','')), 1)
            if tipe == "Maintenance":
                pdf.cell(w[1], 10, str(r.get('periode','')), 1)
                pdf.cell(w[2], 10, str(r.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(r.get('kondisi','')), 1)
                pdf.cell(w[4], 10, str(r.get('keterangan',''))[:90], 1)
            else:
                pdf.cell(w[1], 10, str(r.get('masalah',''))[:40], 1)
                pdf.cell(w[2], 10, str(r.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(r.get('status','')), 1)
                pdf.cell(w[4], 10, str(r.get('tindakan_perbaikan',''))[:70], 1)
            pdf.ln()

        # Signature
        pdf.ln(10); pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, "Known,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
        pdf.cell(138, 5, str(peg.get('Position', 'Pegawai')), 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
        pdf.ln(20); pdf.set_font("Helvetica", "BU", 10)
        pdf.cell(138, 5, str(peg.get('nama', '')), 0, 0, "C"); pdf.cell(138, 5, str(tek.get('nama', '')), 0, 1, "C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, str(peg.get('Jabatan_pdf', '')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")

        # Lampiran Foto
        if tipe != "Maintenance":
            pdf.add_page(); pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 10, "LAMPIRAN FOTO", ln=True, align="C"); pdf.ln(5)
            for _, r in df.iterrows():
                urls = [r.get('foto_kerusakan_url'), r.get('foto_setelah_perbaikan_url')]
                pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 7, f"Unit: {r['Nama Aset']}", ln=True)
                curr_y = pdf.get_y()
                for i, url in enumerate(urls):
                    if url and str(url) != "None":
                        try:
                            res = requests.get(url, timeout=10)
                            if res.status_code == 200:
                                img_data = io.BytesIO(res.content)
                                # Gunakan library tempfile atau simpan sementara untuk hindari error rfind
                                with open("temp_img.jpg", "wb") as f: f.write(res.content)
                                pdf.image("temp_img.jpg", x=10 + (i*70), y=curr_y, w=60)
                                pdf.set_xy(10 + (i*70), curr_y + 42); pdf.cell(60, 5, "Before" if i==0 else "After", 0, 0, "C")
                        except: pass
                pdf.ln(55)
                if pdf.get_y() > 200: pdf.add_page()
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Gagal PDF: {e}"); return None

# --- 6. ROUTING HALAMAN ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
if qr_code_detected and 'qr_handled' not in st.session_state:
    st.session_state.hal = 'LandingQR'; st.session_state.qr_handled = True

st.markdown("""<div class="main-header"><h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1></div>""", unsafe_allow_html=True)

# (Bagian Menu & Form Checklist sama seperti sebelumnya, pastikan fungsi upload_foto & generate_pdf_paripurna terpanggil dengan benar)
# Contoh pemanggilan di hal Export:
# b = generate_pdf_paripurna(df_f, f"{dr[0]} - {dr[1]}", staff_map[p], staff_map[t], "LAPORAN", "Maintenance" if tipe_lap=="Checklist Maintenance" else "Gangguan")
# if b: st.download_button("Download PDF", b, "Laporan.pdf")

# Tambahkan tombol kembali ke menu utama di setiap halaman
if st.session_state.hal != 'Menu':
    if st.button("🏠 KEMBALI KE MENU UTAMA"):
        st.session_state.hal = 'Menu'
        st.rerun()

# --- BAGIAN MENU UTAMA ---
if st.session_state.hal == 'Menu':
    c1, c2 = st.columns(2)
    with c1:
        if st.button("☀️ HARIAN"): st.session_state.hal = 'Harian'; st.rerun()
        if st.button("📅 MINGGUAN"): st.session_state.hal = 'Mingguan'; st.rerun()
        if st.button("🏆 BULANAN"): st.session_state.hal = 'Bulanan'; st.rerun()
    with c2:
        if st.button("⚠️ GANGGUAN"): st.session_state.hal = 'Gangguan'; st.rerun()
        if st.button("🔄 UPDATE PERBAIKAN"): st.session_state.hal = 'Update'; st.rerun()
        if st.button("📑 LAPORAN PDF"): st.session_state.hal = 'Export'; st.rerun()