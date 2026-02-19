import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP BI BPP", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. CSS FIX (ICON DI ATAS TEKS & GLASSMORPHISM) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background: radial-gradient(circle, #0f172a 0%, #020617 100%); }

    .main-header {
        text-align: center; padding: 30px;
        background: rgba(30, 58, 138, 0.1);
        border-bottom: 2px solid #38bdf8;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
        margin-bottom: 40px; border-radius: 0 0 20px 20px;
    }
    .main-header h1 { color: #f8fafc; text-shadow: 0 0 12px #38bdf8; margin: 0; }

    /* Fix Layout Tombol: Ikon Di Atas Teks */
    div.stButton > button {
        width: 100%; height: 190px !important;
        border-radius: 20px !important;
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        backdrop-filter: blur(5px);
        transition: 0.4s ease;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div.stButton > button:hover {
        background: rgba(56, 189, 248, 0.1) !important;
        border: 1px solid #38bdf8 !important;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.4) !important;
        transform: translateY(-8px);
    }

    .btn-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        pointer-events: none;
        margin-top: -150px; /* Menyesuaikan posisi teks di atas button asli */
    }
    .btn-text {
        font-weight: 700; color: #38bdf8; font-size: 0.9rem;
        margin-top: 10px; letter-spacing: 1px;
        text-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
        text-transform: uppercase;
    }

    /* Form Styling */
    label { color: #38bdf8 !important; font-weight: bold; }
    .stSelectbox, .stTextInput, .stTextArea { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI LOGIKA (DATABASE & PDF) ---
@st.cache_data(ttl=60)
def get_assets(): return supabase.table("assets").select("*").order("nama_aset").execute().data
@st.cache_data(ttl=60)
def get_open_issues(): return supabase.table("gangguan_logs").select("*, assets(nama_aset)").neq("status", "Resolved").execute().data
@st.cache_data(ttl=60)
def get_staff(): return supabase.table("staff_me").select("*").execute().data

# --- Fungsi Render SOW ---
def render_sow(nama):
    st.info(f"📋 Parameter SOW: {nama}")
    ck = {}
    if "AC" in nama:
        ck['Filter'] = st.radio("Filter/Evap", ["Bersih", "Kotor"])
        ck['Drainase'] = st.radio("Drainase", ["Lancar", "Sumbat"])
    elif "Genset" in nama:
        ck['Oli'] = st.radio("Level Oli", ["Cukup", "Kurang"])
        ck['Accu'] = st.radio("Tegangan Accu", ["Normal", "Lemah"])
    else:
        ck['Fisik'] = st.radio("Kondisi Fisik", ["OK", "Bermasalah"])
    return ck

# --- 4. NAVIGASI ---
if 'halaman' not in st.session_state: st.session_state.halaman = 'Menu Utama'
def ganti_hal(nama): st.session_state.halaman = nama

# --- 5. HEADER ---
st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI</h1><p>INTEGRATED DIGITAL MAINTENANCE</p></div>', unsafe_allow_html=True)

# --- 6. DATA HANDLING ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}
staff_all = get_staff()
list_tek = [s['nama'] for s in staff_all if s['kategori'] == 'TEKNISI']

# --- 7. MENU UTAMA ---
if st.session_state.halaman == 'Menu Utama':
    st.write("##")
    _, col_p, _ = st.columns([0.1, 0.8, 0.1])
    with col_p:
        m1, m2 = st.columns(2)
        with m1:
            if st.button(" ", key="m1"): ganti_hal('Rutin'); st.rerun()
            st.markdown('<div class="btn-container"><img src="https://img.icons8.com/neon/96/checklist.png" width="70"><div class="btn-text">Checklist Rutin</div></div>', unsafe_allow_html=True)
            st.write("##")
            if st.button(" ", key="m2"): ganti_hal('Update'); st.rerun()
            st.markdown('<div class="btn-container"><img src="https://img.icons8.com/neon/96/refresh.png" width="70"><div class="btn-text">Update Perbaikan</div></div>', unsafe_allow_html=True)
        with m2:
            if st.button(" ", key="m3"): ganti_hal('Gangguan'); st.rerun()
            st.markdown('<div class="btn-container"><img src="https://img.icons8.com/neon/96/error.png" width="70"><div class="btn-text">Lapor Gangguan</div></div>', unsafe_allow_html=True)
            st.write("##")
            if st.button(" ", key="m4"): ganti_hal('Export'); st.rerun()
            st.markdown('<div class="btn-container"><img src="https://img.icons8.com/neon/96/combo-chart.png" width="70"><div class="btn-text">Dashboard & PDF</div></div>', unsafe_allow_html=True)

# --- 8. HALAMAN MODUL ---
else:
    if st.button("⬅️ KEMBALI KE MENU"): ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Checklist Rutin")
        sel = st.selectbox("Pilih Aset", list(options.keys()))
        aset = options[sel]
        with st.form("f_rutin"):
            tek = st.selectbox("Teknisi", list_tek)
            res = render_sow(aset['nama_aset'])
            kon = st.radio("Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
            ket = st.text_area("Keterangan Tambahan")
            
            # --- KEMBALI MENGGUNAKAN CHECKBOX KAMERA ---
            pake_kamera = st.checkbox("📸 Aktifkan Kamera untuk Bukti")
            foto = st.camera_input("Ambil Foto") if pake_kamera else None
            
            if st.form_submit_button("Simpan Laporan SOW"):
                # Logika simpan tetap sama
                st.success("Tersimpan!")

    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Lapor Gangguan")
        # ... (Logika form gangguan dengan checkbox kamera juga)
        with st.form("f_gng"):
            st.selectbox("Pilih Aset", list(options.keys()))
            st.text_area("Masalah")
            pake_kamera_g = st.checkbox("📸 Aktifkan Kamera")
            foto_g = st.camera_input("Foto") if pake_kamera_g else None
            st.form_submit_button("Kirim")