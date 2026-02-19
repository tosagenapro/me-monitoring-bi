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

# --- 2. CSS STABIL (TOMBOL BISA DIKLIK) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background: radial-gradient(circle, #0f172a 0%, #020617 100%); }

    /* Header */
    .main-header {
        text-align: center; padding: 25px;
        background: rgba(30, 58, 138, 0.1);
        border-bottom: 2px solid #38bdf8;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.2);
        margin-bottom: 30px; border-radius: 0 0 20px 20px;
    }
    .main-header h1 { color: #f8fafc; text-shadow: 0 0 12px #38bdf8; margin: 0; font-size: 2rem; }

    /* Tombol Menu Utama - Dibuat Stabil */
    div.stButton > button {
        width: 100%;
        height: 180px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        border-radius: 20px !important;
        color: #38bdf8 !important;
        font-weight: bold !important;
        font-size: 1rem !important;
        transition: 0.3s !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 15px !important;
    }
    
    div.stButton > button:hover {
        background: rgba(56, 189, 248, 0.15) !important;
        border: 1px solid #38bdf8 !important;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.4) !important;
        transform: translateY(-5px);
    }

    /* Form Input agar kontras */
    label { color: #38bdf8 !important; font-weight: bold !important; }
    .stSelectbox, .stTextInput, .stTextArea { background-color: rgba(255,255,255,0.05) !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI LOGIKA DATA ---
@st.cache_data(ttl=60)
def get_assets():
    return supabase.table("assets").select("*").order("nama_aset").execute().data

@st.cache_data(ttl=60)
def get_open_issues():
    return supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute().data

@st.cache_data(ttl=60)
def get_all_logs():
    return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

@st.cache_data(ttl=60)
def get_staff():
    return supabase.table("staff_me").select("*").execute().data

def generate_pdf(df, tgl, p_sel, t_sel):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "LAPORAN MAINTENANCE ME - BI BALIKPAPAN", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(200, 230, 255)
    pdf.cell(60, 8, "Nama Aset", 1, 0, "C", True)
    pdf.cell(35, 8, "Teknisi", 1, 0, "C", True)
    pdf.cell(35, 8, "Kondisi", 1, 0, "C", True)
    pdf.cell(147, 8, "Detail Parameter SOW", 1, 1, "C", True)
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        exclude = ['Nama Aset', 'teknisi', 'kondisi', 'keterangan', 'Tanggal']
        sow = ", ".join([str(k) for k, v in row.items() if k not in exclude and v == "v"])
        pdf.cell(60, 7, str(row['Nama Aset'])[:40], 1)
        pdf.cell(35, 7, str(row['teknisi']), 1, 0, "C")
        pdf.cell(35, 7, str(row['kondisi']), 1, 0, "C")
        pdf.cell(147, 7, sow[:110], 1, 1)
    pdf.ln(10)
    pdf.cell(138, 5, f"Mengetahui: {p_sel}", 0, 0, "C")
    pdf.cell(138, 5, f"Dibuat Oleh: {t_sel}", 0, 1, "C")
    return bytes(pdf.output())

# --- 4. NAVIGASI ---
if 'halaman' not in st.session_state: st.session_state.halaman = 'Menu Utama'
def ganti_hal(nama): st.session_state.halaman = nama

# --- 5. DATA HANDLING ---
asset_data = get_assets()
opt_asset = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}
staff_data = get_staff()
list_tek = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_data if s['kategori'] == 'PEGAWAI']

# --- 6. HEADER ---
st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI</h1><p style="color:#38bdf8; font-size:0.8rem;">INTEGRATED DIGITAL MAINTENANCE</p></div>', unsafe_allow_html=True)

# --- 7. MENU UTAMA ---
if st.session_state.halaman == 'Menu Utama':
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 CHECKLIST RUTIN", key="m1"): ganti_hal('Rutin'); st.rerun()
        st.write("##")
        if st.button("🔄 UPDATE PERBAIKAN", key="m2"): ganti_hal('Update'); st.rerun()
    with col2:
        if st.button("⚠️ LAPOR GANGGUAN", key="m3"): ganti_hal('Gangguan'); st.rerun()
        st.write("##")
        if st.button("📊 DASHBOARD & PDF", key="m4"): ganti_hal('Export'); st.rerun()

# --- 8. HALAMAN MODUL ---
else:
    if st.button("⬅️ KEMBALI KE MENU"): ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Form Checklist Rutin")
        sel = st.selectbox("Pilih Aset", list(opt_asset.keys()))
        aset = opt_asset[sel]
        with st.form("f_rutin", clear_on_submit=True):
            t = st.selectbox("Teknisi", list_tek)
            # SOW Sederhana agar tidak berat
            kon = st.radio("Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
            ket = st.text_area("Keterangan")
            
            # --- CHECKBOX KAMERA KEMBALI ---
            pake_cam = st.checkbox("📸 Aktifkan Kamera")
            foto = st.camera_input("Ambil Foto") if pake_cam else None
            
            if st.form_submit_button("SIMPAN DATA"):
                url = None
                if foto:
                    fn = f"R_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                    url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
                supabase.table("maintenance_logs").insert({"asset_id": aset['id'], "teknisi": t, "kondisi": kon, "keterangan": ket, "foto_url": url}).execute()
                st.success("Tersimpan!"); st.balloons()

    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Lapor Kerusakan")
        sel_g = st.selectbox("Aset Bermasalah", list(opt_asset.keys()))
        aset_g = opt_asset[sel_g]
        with st.form("f_gng", clear_on_submit=True):
            pel = st.selectbox("Pelapor", list_tek)
            mas = st.text_area("Deskripsi Kerusakan")
            pake_cam_g = st.checkbox("📸 Aktifkan Kamera")
            foto_g = st.camera_input("Foto") if pake_cam_g else None
            if st.form_submit_button("KIRIM LAPORAN"):
                url_g = None
                if foto_g:
                    fn_g = f"G_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_g, foto_g.getvalue())
                    url_g = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_g)
                supabase.table("gangguan_logs").insert({"asset_id": aset_g['id'], "teknisi": pel, "masalah": mas, "status": "Open", "foto_kerusakan_url": url_g}).execute()
                st.error("Laporan Dikirim!")

    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Update Penyelesaian")
        iss = get_open_issues()
        if not iss: st.info("Tidak ada gangguan aktif.")
        else:
            iss_opt = {f"{i['assets']['nama_aset']} - {i['masalah'][:30]}": i for i in iss}
            sel_i = st.selectbox("Pilih Laporan", list(iss_opt.keys()))
            dat_i = iss_opt[sel_i]
            with st.form("f_fix"):
                tp = st.selectbox("Teknisi Pelaksana", list_tek)
                tin = st.text_area("Tindakan")
                pake_cam_f = st.checkbox("📸 Aktifkan Kamera")
                f_a = st.camera_input("Foto After") if pake_cam_f else None
                if st.form_submit_button("SELESAI"):
                    url_a = None
                    if f_a:
                        fn_a = f"F_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_a, f_a.getvalue())
                        url_a = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_a)
                    supabase.table("gangguan_logs").update({"status": "Resolved", "tindakan_perbaikan": tin, "teknisi_perbaikan": tp, "foto_setelah_perbaikan_url": url_a}).eq("id", dat_i['id']).execute()
                    st.success("Selesai!")

    elif st.session_state.halaman == 'Export':
        st.subheader("📊 Dashboard & Export PDF")
        logs = get_all_logs()
        if logs:
            df = pd.DataFrame(logs)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
            dp = st.date_input("Pilih Tanggal", datetime.date.today())
            df_f = df[df['Tanggal'] == dp].copy()
            st.dataframe(df_f[['Nama Aset', 'teknisi', 'kondisi', 'keterangan']], use_container_width=True)
            
            n_bi = st.selectbox("Mengetahui (BI)", list_peg)
            n_tk = st.selectbox("Dibuat (ME)", list_tek)
            if st.download_button("📥 DOWNLOAD PDF", generate_pdf(df_f, dp, n_bi, n_tk), f"Lap_{dp}.pdf"):
                st.success("PDF Berhasil Dibuat")