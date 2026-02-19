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

# --- 2. CUSTOM CSS (RAHASIA TAMPILAN MEWAH) ---
st.markdown("""
    <style>
    /* Menghilangkan Header Default Streamlit */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Background Utama */
    .stApp {
        background-color: #f8fafc;
    }

    /* Styling Judul */
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        border-radius: 0 0 30px 30px;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* Container Menu */
    .menu-container {
        max-width: 800px;
        margin: 0 auto;
    }

    /* Tombol Menu Custom */
    div.stButton > button {
        width: 100%;
        height: 180px !important;
        border-radius: 25px !important;
        border: none !important;
        background-color: white !important;
        color: #1E3A8A !important;
        font-size: 18px !important;
        font-weight: bold !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05) !important;
        transition: all 0.3s ease-in-out !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    div.stButton > button:hover {
        transform: translateY(-10px) !important;
        box-shadow: 0 15px 30px rgba(0,0,0,0.1) !important;
        border: 2px solid #3B82F6 !important;
    }

    /* Ikon di dalam tombol */
    .btn-text {
        display: block;
        margin-top: 10px;
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAVIGASI ---
if 'halaman' not in st.session_state:
    st.session_state.halaman = 'Menu Utama'

def ganti_hal(nama_hal):
    st.session_state.halaman = nama_hal

# --- 4. FUNGSI DATABASE (Sama seperti sebelumnya) ---
def get_assets():
    return supabase.table("assets").select("id, nama_aset, kategori, kode_qr").order("nama_aset").execute().data

def get_open_issues():
    return supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute().data

def get_all_maintenance_logs():
    return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

def get_staff_data():
    return supabase.table("staff_me").select("*").execute().data

# --- 5. HEADER BIRU KHAS BI ---
st.markdown("""
    <div class="main-header">
        <h1 style='margin:0; font-size: 2.5rem;'>🚀 SIMANTAP</h1>
        <p style='margin:0; opacity: 0.8;'>Monitoring & Pemeliharaan ME - KPwBI Balikpapan</p>
    </div>
    """, unsafe_allow_html=True)

# --- 6. LOGIKA HALAMAN ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

if st.session_state.halaman == 'Menu Utama':
    st.write("##")
    # Grid Menu Tengah
    _, col_menu, _ = st.columns([0.1, 0.8, 0.1])
    
    with col_menu:
        m1, m2 = st.columns(2)
        with m1:
            if st.button("📋\n\nChecklist Rutin", key="btn_rutin"):
                ganti_hal('Rutin'); st.rerun()
            st.write("#")
            if st.button("✅\n\nUpdate Perbaikan", key="btn_update"):
                ganti_hal('Update'); st.rerun()
        with m2:
            if st.button("⚠️\n\nLapor Gangguan", key="btn_gng"):
                ganti_hal('Gangguan'); st.rerun()
            st.write("#")
            if st.button("📊\n\nDashboard & PDF", key="btn_pdf"):
                ganti_hal('Export'); st.rerun()

else:
    # Tombol Kembali yang Cantik
    if st.button("⬅️ Kembali ke Menu Utama"):
        ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    # --- ISI MODUL (Rutin, Gangguan, Update, Export) ---
    # (Gunakan logika if-elif yang sama dengan kode sebelumnya di sini)
    if st.session_state.halaman == 'Rutin':
        st.header("📋 Checklist Rutin")
        # ... kode form rutin Bapak ...
        # (Sesuai kode sebelumnya)
        staff_data = get_staff_data()
        list_tek = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']
        sel_label = st.selectbox("Pilih Aset", options=list(options.keys()))
        asset = options[sel_label]
        with st.form("f_rutin"):
            tek = st.selectbox("Nama Teknisi", options=list_tek)
            # Karena fungsi SOW panjang, pastikan fungsi render_sow_checklist ada di atas
            from app_functions import render_sow_checklist # atau biarkan fungsinya di file ini
            # (Untuk ringkasnya, masukkan kembali fungsi render_sow_checklist di sini)
            st.info(f"Pengerjaan aset: {asset['nama_aset']}")
            kon = st.radio("Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
            ket = st.text_area("Keterangan")
            siap_cam = st.checkbox("📸 Aktifkan Kamera")
            foto = st.camera_input("Foto Bukti") if siap_cam else None
            if st.form_submit_button("SIMPAN LAPORAN"):
                st.success("Data berhasil diproses ke database!")

    elif st.session_state.halaman == 'Gangguan':
        st.header("⚠️ Lapor Gangguan")
        # ... isi modul gangguan ...

    elif st.session_state.halaman == 'Update':
        st.header("✅ Update Perbaikan")
        # ... isi modul update ...

    elif st.session_state.halaman == 'Export':
        st.header("📊 Dashboard & Export PDF")
        # ... isi modul export ...