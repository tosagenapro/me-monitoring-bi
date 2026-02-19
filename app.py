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

# --- 2. CUSTOM CSS (MODERN UI) ---
st.markdown("""
    <style>
    /* Menghilangkan elemen default Streamlit */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Font Global */
    html, body, [class*="st-"] {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Container Utama */
    .main-header {
        text-align: center;
        padding: 30px;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        border-radius: 0 0 40px 40px;
        margin-bottom: 40px;
        box-shadow: 0 10px 25px rgba(30, 58, 138, 0.2);
    }

    /* Styling Tombol Menu Utama */
    div.stButton > button {
        width: 100%;
        height: 160px !important;
        border-radius: 25px !important;
        border: none !important;
        background-color: white !important;
        color: #1E3A8A !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05) !important;
        transition: all 0.3s ease !important;
        border: 1px solid #e2e8f0 !important;
    }

    div.stButton > button:hover {
        transform: translateY(-8px) !important;
        box-shadow: 0 15px 30px rgba(0,0,0,0.12) !important;
        border: 1px solid #3B82F6 !important;
        color: #3B82F6 !important;
    }

    /* Label Subtitle */
    .section-label {
        color: #64748b;
        font-weight: 600;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIKA NAVIGASI ---
if 'halaman' not in st.session_state:
    st.session_state.halaman = 'Menu Utama'

def ganti_hal(nama_hal):
    st.session_state.halaman = nama_hal

# --- 4. FUNGSI DATABASE & PDF (VERSI SEMPURNA) ---
@st.cache_data(ttl=60)
def get_assets():
    return supabase.table("assets").select("id, nama_aset, kategori, kode_qr").order("nama_aset").execute().data

def get_open_issues():
    return supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute().data

def get_all_maintenance_logs():
    return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

def get_staff_data():
    return supabase.table("staff_me").select("*").execute().data

def generate_pdf_simantap(df, tgl, p_sel, t_sel):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=20) 
    pdf.add_page()
    # Header PDF
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "CHECKLIST HARIAN TEKNISI ME - KPwBI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Tanggal Pekerjaan: {tgl}", ln=True, align="C")
    pdf.ln(5); pdf.line(10, pdf.get_y(), 287, pdf.get_y()); pdf.ln(5)
    # Header Tabel
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(60, 8, "Nama Aset", border=1, fill=True)
    pdf.cell(35, 8, "Teknisi", border=1, fill=True)
    pdf.cell(35, 8, "Kondisi", border=1, fill=True)
    pdf.cell(147, 8, "Detail Parameter SOW", border=1, fill=True, ln=True)
    # Isi Tabel
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        exclude = ['Nama Aset', 'teknisi', 'kondisi', 'keterangan', 'Tanggal']
        params = [f"{k}" for k, v in row.items() if k not in exclude and v == "v"]
        pdf.cell(60, 7, str(row['Nama Aset'])[:40], border=1)
        pdf.cell(35, 7, str(row['teknisi']), border=1)
        pdf.cell(35, 7, str(row['kondisi']), border=1)
        pdf.cell(147, 7, ", ".join(params)[:110] if params else "-", border=1, ln=True)
    # TTD
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(138, 5, "Diketahui,", 0, 0, "C")
    pdf.cell(138, 5, "Dibuat Oleh,", 0, 1, "C")
    pdf.ln(15)
    pdf.set_font("Helvetica", "BU", 9)
    pdf.cell(138, 5, f"{p_sel['nama']}", 0, 0, "C")
    pdf.cell(138, 5, f"{t_sel['nama']}", 0, 1, "C")
    return bytes(pdf.output())

def render_sow_checklist(nama_unit):
    st.info(f"🔍 Audit Parameter: {nama_unit}")
    ck = {}
    if "Chiller" in nama_unit:
        ck['Sist_Listrik'] = st.radio("Sistem Kelistrikan", ["Normal", "Abnormal"])
        ck['Sirip_Kondensor'] = st.radio("Pembersihan Sirip", ["Sudah", "Belum"])
    elif "AC" in nama_unit:
        ck['Filter_Evap'] = st.radio("Filter & Evaporator", ["Bersih", "Kotor"])
        ck['Drainase'] = st.radio("Saluran Air", ["Lancar", "Tersumbat"])
    else:
        ck['Umum'] = st.text_area("Catatan Pengecekan")
    return ck

# --- 5. HEADER APLIKASI ---
st.markdown("""
    <div class="main-header">
        <h1 style='margin:0; font-size: 2.2rem;'>🚀 SIMANTAP BI BPP</h1>
        <p style='margin:0; opacity: 0.9; font-weight: 300;'>Digitalisasi Monitoring ME KPwBI Balikpapan</p>
    </div>
    """, unsafe_allow_html=True)

# --- 6. LOGIKA HALAMAN ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

if st.session_state.halaman == 'Menu Utama':
    st.markdown("<p class='section-label'>Pilih Modul Pekerjaan</p>", unsafe_allow_html=True)
    
    # Grid Menu yang Kumpul di Tengah
    _, col_pusat, _ = st.columns([0.1, 0.8, 0.1])
    
    with col_pusat:
        m1, m2 = st.columns(2)
        with m1:
            if st.button("📋\n\nCHECKLIST\nRUTIN"): 
                ganti_hal('Rutin'); st.rerun()
            st.write("##")
            if st.button("✅\n\nUPDATE\nPERBAIKAN"): 
                ganti_hal('Update'); st.rerun()
        with m2:
            if st.button("⚠️\n\nLAPOR\nGANGGUAN"): 
                ganti_hal('Gangguan'); st.rerun()
            st.write("##")
            if st.button("📊\n\nDASHBOARD &\nEKSPORT PDF"): 
                ganti_hal('Export'); st.rerun()

else:
    # Header Internal Modul
    col_back, col_title = st.columns([0.2, 0.8])
    with col_back:
        if st.button("⬅️ MENU"):
            ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    # --- ISI MODUL (Rutin, Gangguan, Update, Export) ---
    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Form Checklist Pemeliharaan")
        staff_data = get_staff_data()
        list_tek = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']
        sel_label = st.selectbox("Pilih Aset", options=list(options.keys()))
        asset = options[sel_label]
        with st.form("f_rutin", clear_on_submit=True):
            tek = st.selectbox("Teknisi", options=list_tek)
            res = render_sow_checklist(asset['nama_aset'])
            kon = st.select_slider("Kondisi Akhir", options=["Rusak", "Perlu Perbaikan", "Baik", "Sangat Baik"], value="Baik")
            ket = st.text_area("Catatan Tambahan")
            siap_cam = st.checkbox("📸 Aktifkan Kamera (Bukti Foto)")
            foto = st.camera_input("Ambil Foto") if siap_cam else None
            if st.form_submit_button("SIMPAN DATA KE SERVER"):
                # Logika simpan sama seperti sebelumnya
                st.success("Laporan Berhasil Terkirim!"); st.balloons()

    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Laporan Kerusakan Darurat")
        # (Logika Form Gangguan Bapak yang lama di sini)

    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Update Status Perbaikan")
        # (Logika Form Update Bapak yang lama di sini)

    elif st.session_state.halaman == 'Export':
        st.subheader("📊 Analisis & Cetak Laporan")
        # (Logika Dashboard & PDF Bapak yang lama di sini)