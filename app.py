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

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP ME BI BPP", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. QR DETECTOR LOGIC ---
qr_code_detected = st.query_params.get("unit")
BASE_URL_APP = "https://simantap-bi-bpp.streamlit.app"

# --- 3. MASTER SOW ---
SOW_MASTER = {
    "AC": {"Harian": ["Suhu Ruangan (°C)", "Suara Abnormal", "Kebocoran Air"], "Mingguan": ["Filter Udara", "Remote"], "Bulanan": ["Freon (Psi)", "Cuci Evap"]},
    "AHU": {"Harian": ["Tekanan Udara (Pa)", "V-Belt"], "Mingguan": ["Pre-filter", "Arus Motor"], "Bulanan": ["Cleaning Coil"]},
    "GENSET": {"Harian": ["BBM (%)", "Oli", "Baterai (Volt)"], "Mingguan": ["Running Test", "Kebocoran"], "Bulanan": ["Output Volt", "Freq (Hz)"]},
    "UPS": {"Harian": ["Kapasitas (%)", "Input (Volt)"], "Mingguan": ["Output (Volt)", "Suhu Bat"], "Bulanan": ["Uji Discharge"]},
    "PANEL": {"Harian": ["Lampu Indikator", "Suhu Ruang"], "Mingguan": ["MCB", "Debu"], "Bulanan": ["Beban (Ampere)", "Thermography"]},
    "UMUM": {"Harian": ["Kebersihan", "Fungsi"], "Mingguan": ["Fisik"], "Bulanan": ["Performa"]}
}

# --- 4. CSS MODERN & HEADER PARIPURNA ---
st.markdown(f"""
    <style>
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    .stApp {{ background: #0f172a; }}
    .main-header {{
        text-align: center; padding: 25px; 
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
        border-bottom: 3px solid #38bdf8; border-radius: 0 0 25px 25px; margin-bottom: 30px;
    }}
    .main-header h1 {{ color: #38bdf8; margin: 0; font-size: 1.8rem; font-weight: 800; }}
    .main-header p {{ color: #f8fafc; font-weight: 500; font-size: 1.1rem; margin: 12px 0 0 0; }}
    </style>
    <div class="main-header">
        <h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1>
        <p>Sistem Informasi Monitoring Aset dan Tindakan Pemeliharaan Terpadu</p>
    </div>
    """, unsafe_allow_html=True)

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
    if not file: return None
    fname = f"{uuid.uuid4()}.jpg"
    try:
        supabase.storage.from_("foto_maintenance").upload(fname, file.getvalue(), {"content-type":"image/jpeg"})
        return f"{URL}/storage/v1/object/public/foto_maintenance/{fname}"
    except: return None

def generate_pdf_final(df, rentang, peg, tek, judul, tipe="Maintenance"):
    pdf = FPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"{judul} - KPwBI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 10); pdf.cell(0, 7, f"Periode: {rentang}", ln=True, align="C"); pdf.ln(10)
    
    # Table Header
    pdf.set_font("Helvetica", "B", 8); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255)
    w = [60, 30, 30, 30, 110]
    cols = ["Nama Aset", "Periode/Status", "Teknisi", "Kondisi", "Detail"]
    for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
    pdf.ln(); pdf.set_font("Helvetica", "", 7); pdf.set_text_color(0)
    
    for _, r in df.iterrows():
        pdf.cell(w[0], 10, str(r.get('Nama Aset','')), 1)
        pdf.cell(w[1], 10, str(r.get('periode' if tipe=="Maintenance" else 'status','')), 1)
        pdf.cell(w[2], 10, str(r.get('teknisi','')), 1)
        pdf.cell(w[3], 10, str(r.get('kondisi','-')), 1)
        pdf.cell(w[4], 10, str(r.get('keterangan' if tipe=="Maintenance" else 'masalah',''))[:80], 1); pdf.ln()

    # Signature (Sesuai Request: Known, Position, Name Underlined, Jabatan_pdf)
    pdf.ln(10); pdf.set_font("Helvetica", "", 10)
    pdf.cell(138, 5, "Known,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
    pdf.cell(138, 5, str(peg.get('posisi','')).replace('"', ''), 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
    pdf.ln(18)
    pdf.set_font("Helvetica", "BU", 10) # Underlined
    pdf.cell(138, 5, str(peg.get('nama','')), 0, 0, "C"); pdf.cell(138, 5, str(tek.get('nama','')), 0, 1, "C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(138, 5, str(peg.get('jabatan_pdf','')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")
    return pdf.output(dest='S').encode('latin-1')

# --- 6. ROUTING ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
if qr_code_detected: st.session_state.hal = 'LandingQR'

# --- 7. HALAMAN ---
if st.session_state.hal == 'Menu':
    c1, c2 = st.columns(2)
    with c1:
        if st.button("☀️ HARIAN"): st.session_state.hal = 'Harian'; st.rerun()
        if st.button("📅 MINGGUAN"): st.session_state.hal = 'Mingguan'; st.rerun()
        if st.button("🏆 BULANAN"): st.session_state.hal = 'Bulanan'; st.rerun()
    with c2:
        if st.button("⚠️ GANGGUAN"): st.session_state.hal = 'Gangguan'; st.rerun()
        if st.button("🔄 UPDATE"): st.session_state.hal = 'Update'; st.rerun()
        if st.button("📑 LAPORAN"): st.session_state.hal = 'Export'; st.rerun()

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    asset_data = qr_map.get(qr_code_detected) if qr_code_detected else opt_asset[st.selectbox("Pilih Unit:", list(opt_asset.keys()))]
    st.info(f"Unit: {asset_data['nama_aset']}")
    with st.form("f_chk"):
        tek = st.selectbox("Teknisi", [s['nama'] for s in staff_list if s['kategori']=='TEKNISI'])
        kat = asset_data.get('kategori', 'UMUM').upper()
        tasks = SOW_MASTER.get(kat, SOW_MASTER['UMUM'])[st.session_state.hal]
        res = []
        for t in tasks:
            val = st.radio(t, ["Normal", "Abnormal", "N/A"], horizontal=True)
            res.append(f"{t}: {val}")
        kon = st.select_slider("Kondisi", ["Rusak", "Perlu Perbaikan", "Baik", "Sangat Baik"], "Baik")
        if st.form_submit_button("💾 SIMPAN"):
            supabase.table("maintenance_logs").insert({"asset_id": asset_data['id'], "teknisi": tek, "periode": st.session_state.hal, "kondisi": kon, "keterangan": " | ".join(res)}).execute()
            st.success("Berhasil!"); time.sleep(1); st.session_state.hal = 'Menu'; st.rerun()
    if st.button("⬅️ Batal"): st.session_state.hal = 'Menu'; st.rerun()

elif st.session_state.hal == 'Gangguan':
    asset_data = qr_map.get(qr_code_detected) if qr_code_detected else opt_asset[st.selectbox("Pilih Aset", list(opt_asset.keys()))]
    with st.form("f_g"):
        pel = st.selectbox("Pelapor", [s['nama'] for s in staff_list if s['kategori']=='TEKNISI'])
        mas = st.text_area("Detail Masalah")
        foto = st.camera_input("Ambil Foto")
        if st.form_submit_button("🚨 KIRIM"):
            u = upload_foto(foto)
            supabase.table("gangguan_logs").insert({"asset_id": asset_data['id'], "teknisi": pel, "masalah": mas, "status": "Open", "foto_kerusakan_url": u}).execute()
            st.warning("Laporan Terkirim!"); time.sleep(1); st.session_state.hal = 'Menu'; st.rerun()
    if st.button("⬅️ Batal"): st.session_state.hal = 'Menu'; st.rerun()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ Kembali"): st.session_state.hal = 'Menu'; st.rerun()
    tipe = st.radio("Tipe:", ["Maintenance", "Gangguan"])
    dr = st.date_input("Rentang Waktu", [datetime.date.today()-datetime.timedelta(days=7), datetime.date.today()])
    if len(dr) == 2:
        tbl = "maintenance_logs" if tipe == "Maintenance" else "gangguan_logs"
        raw = supabase.table(tbl).select("*, assets(nama_aset)").execute().data
        if raw:
            df = pd.DataFrame(raw); df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'])
            df_f = df[(pd.to_datetime(df['created_at']).dt.date >= dr[0]) & (pd.to_datetime(df['created_at']).dt.date <= dr[1])]
            st.dataframe(df_f[['Nama Aset', 'teknisi', 'created_at']], use_container_width=True)
            p = st.selectbox("Diketahui (Pegawai):", [s['nama'] for s in staff_list if s['kategori']=='PEGAWAI'])
            t = st.selectbox("Dibuat (Teknisi):", [s['nama'] for s in staff_list if s['kategori']=='TEKNISI'])
            if st.button("📄 DOWNLOAD PDF"):
                b = generate_pdf_final(df_f, f"{dr[0]} - {dr[1]}", staff_map[p], staff_map[t], "LAPORAN", tipe)
                st.download_button("Klik Simpan", b, "Laporan_SIMANTAP.pdf")

elif st.session_state.hal == 'LandingQR':
    a = qr_map.get(qr_code_detected)
    if a:
        st.success(f"📍 TERDETEKSI: {a['nama_aset']}")
        if st.button("BUKA MENU"): st.query_params.clear(); st.session_state.hal = 'Menu'; st.rerun()
    else: st.error("QR Tidak Dikenal"); st.button("Menu Utama", on_click=lambda: st.session_state.update({"hal": "Menu"}))