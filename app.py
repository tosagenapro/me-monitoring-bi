import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import json

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP BI BPP", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. CSS ANTI-EROR (STABIL DI HP) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background: #0f172a; }

    /* Header */
    .main-header {
        text-align: center; padding: 20px;
        background: #1e293b;
        border-bottom: 3px solid #38bdf8;
        margin-bottom: 20px;
        border-radius: 0 0 15px 15px;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.5rem; text-shadow: 0 0 10px #38bdf8; }

    /* Tombol Menu Utama */
    div.stButton > button {
        width: 100%;
        height: 100px !important;
        background: #1e293b !important;
        border: 2px solid #334155 !important;
        border-radius: 12px !important;
        color: #38bdf8 !important;
        font-weight: bold !important;
        font-size: 0.9rem !important;
        margin-bottom: 10px;
        white-space: pre-wrap !important;
    }
    
    div.stButton > button:hover {
        border-color: #38bdf8 !important;
        background: #0f172a !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
    }

    /* Input & Label */
    label { color: #38bdf8 !important; font-weight: bold !important; }
    .stSelectbox, .stTextInput, .stTextArea { background-color: #1e293b !important; color: white !important; }
    div[data-testid="stMarkdownContainer"] p { color: #cbd5e1; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI LOGIKA SOW DINAMIS ---
def get_sow_fields(nama_aset, jenis):
    fields = {}
    st.write(f"### 📋 Parameter {jenis}")
    # Logika SOW AC/AHU
    if "AC" in nama_aset or "AHU" in nama_aset:
        if jenis == "Harian":
            fields['suhu_suplai'] = st.text_input("Suhu Suplai (°C)")
            fields['fisik'] = st.radio("Kondisi Unit", ["Normal", "Bising/Getar"])
        elif jenis == "Mingguan":
            fields['filter'] = st.radio("Cek Filter Udara", ["Bersih", "Kotor/Cuci"])
            fields['drainase'] = st.radio("Saluran Air", ["Lancar", "Sumbat"])
        elif jenis == "Bulanan":
            fields['arus_motor'] = st.text_input("Arus Motor (Ampere)")
            fields['tekanan_freon'] = st.text_input("Tekanan Freon (Psi)")
            fields['evaporator'] = st.radio("Kondisi Evap", ["Bersih", "Kotor/Berlendir"])
    # Logika SOW Genset
    elif "Genset" in nama_aset:
        if jenis == "Harian":
            fields['solar'] = st.select_slider("Level Solar", ["Low", "Med", "High"])
            fields['oli'] = st.radio("Level Oli", ["Cukup", "Kurang"])
        elif jenis == "Mingguan":
            fields['accu'] = st.text_input("Tegangan Accu (V)")
            fields['running_test'] = st.radio("Running Test 15 Menit", ["OK", "N/A"])
        elif jenis == "Bulanan":
            fields['filter_oli'] = st.radio("Kondisi Filter", ["Bersih", "Wajib Ganti"])
            fields['radiator'] = st.radio("Air Radiator", ["Cukup", "Kurang"])
    else:
        fields['cek_fisik'] = st.radio("Kondisi Fisik Umum", ["Normal", "Bermasalah"])
    return fields

# --- 4. FUNGSI DATA ---
@st.cache_data(ttl=60)
def get_assets():
    return supabase.table("assets").select("*").order("nama_aset").execute().data

@st.cache_data(ttl=60)
def get_staff():
    return supabase.table("staff_me").select("*").execute().data

@st.cache_data(ttl=60)
def get_open_issues():
    return supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute().data

@st.cache_data(ttl=60)
def get_all_logs():
    return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

def generate_pdf(df, tgl, p_sel, t_sel):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "LAPORAN PEMELIHARAAN ME - BI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Tanggal: {tgl}", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 8); pdf.set_fill_color(200, 230, 255)
    pdf.cell(50, 8, "Nama Aset", 1, 0, "C", True)
    pdf.cell(25, 8, "Periode", 1, 0, "C", True)
    pdf.cell(30, 8, "Teknisi", 1, 0, "C", True)
    pdf.cell(30, 8, "Kondisi", 1, 0, "C", True)
    pdf.cell(142, 8, "Detail SOW / Keterangan", 1, 1, "C", True)
    pdf.set_font("Helvetica", "", 7)
    for _, row in df.iterrows():
        sow = row.get('checklist_data', {})
        sow_txt = " | ".join([f"{k}:{v}" for k, v in sow.items()]) if isinstance(sow, dict) else ""
        pdf.cell(50, 7, str(row['Nama Aset'])[:35], 1)
        pdf.cell(25, 7, str(row.get('periode', '-')), 1, 0, "C")
        pdf.cell(30, 7, str(row['teknisi']), 1, 0, "C")
        pdf.cell(30, 7, str(row['kondisi']), 1, 0, "C")
        pdf.cell(142, 7, (sow_txt + " - " + str(row['keterangan']))[:110], 1, 1)
    pdf.ln(10)
    pdf.cell(138, 5, f"Mengetahui: {p_sel}", 0, 0, "C")
    pdf.cell(138, 5, f"Dibuat Oleh: {t_sel}", 0, 1, "C")
    return bytes(pdf.output())

# --- 5. LOGIKA NAVIGASI ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
def pindah(nama): st.session_state.hal = nama

assets_data = get_assets()
opt_asset = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in assets_data}
staff_data = get_staff()
list_tek = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_data if s['kategori'] == 'PEGAWAI']

# --- 6. HEADER ---
st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI BALIKPAPAN</h1></div>', unsafe_allow_html=True)

# --- 7. ROUTING HALAMAN ---
if st.session_state.hal == 'Menu':
    col1, col2 = st.columns(2)
    with col1:
        if st.button("☀️\nCHECKLIST HARIAN"): pindah('Harian'); st.rerun()
        if st.button("📅\nCHECKLIST MINGGUAN"): pindah('Mingguan'); st.rerun()
        if st.button("🏆\nCHECKLIST BULANAN"): pindah('Bulanan'); st.rerun()
    with col2:
        if st.button("⚠️\nLAPOR GANGGUAN"): pindah('Gangguan'); st.rerun()
        if st.button("🔄\nUPDATE PERBAIKAN"): pindah('Update'); st.rerun()
        if st.button("📊\nDASHBOARD & PDF"): pindah('Export'); st.rerun()

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    curr = st.session_state.hal
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"Form {curr}")
    sel = st.selectbox("Pilih Aset", list(opt_asset.keys()))
    aset = opt_asset[sel]
    with st.form("f_rutin", clear_on_submit=True):
        t = st.selectbox("Teknisi", list_tek)
        res_sow = get_sow_fields(aset['nama_aset'], curr)
        kon = st.radio("Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
        ket = st.text_area("Keterangan Tambahan")
        pake_cam = st.checkbox("📸 Aktifkan Kamera")
        foto = st.camera_input("Ambil Foto") if pake_cam else None
        if st.form_submit_button("SIMPAN DATA"):
            url = None
            if foto:
                fn = f"R_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
            supabase.table("maintenance_logs").insert({
                "asset_id": aset['id'], "teknisi": t, "periode": curr,
                "checklist_data": res_sow, "kondisi": kon, "keterangan": ket, "foto_url": url
            }).execute()
            st.success(f"Laporan {curr} Berhasil!"); st.balloons()

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("⚠️ Lapor Gangguan")
    sel_g = st.selectbox("Pilih Aset Bermasalah", list(opt_asset.keys()))
    with st.form("f_gangguan", clear_on_submit=True):
        pel = st.selectbox("Pelapor", list_tek)
        mas = st.text_area("Deskripsi Kerusakan")
        if st.form_submit_button("KIRIM LAPORAN"):
            supabase.table("gangguan_logs").insert({
                "asset_id": opt_asset[sel_g]['id'], "teknisi": pel, "masalah": mas, "status": "Open"
            }).execute()
            st.error("Laporan Terkirim!")

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("🔄 Update Penyelesaian")
    iss = get_open_issues()
    if not iss: st.info("Tidak ada gangguan aktif.")
    else:
        opt_iss = {f"{i['assets']['nama_aset']} - {i['masalah'][:30]}": i for i in iss}
        sel_i = st.selectbox("Pilih Laporan", list(opt_iss.keys()))
        with st.form("f_fix"):
            tp = st.selectbox("Teknisi Pelaksana", list_tek)
            tin = st.text_area("Tindakan")
            if st.form_submit_button("SELESAI"):
                supabase.table("gangguan_logs").update({
                    "status": "Resolved", "tindakan_perbaikan": tin, "teknisi_perbaikan": tp
                }).eq("id", opt_iss[sel_i]['id']).execute()
                st.success("Status Diupdate!")

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Monitoring & Export Laporan Spesifik")
    
    logs = get_all_logs()
    if logs:
        df = pd.DataFrame(logs)
        df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
        df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
        
        # --- FILTER BARU ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            tgl_awal = st.date_input("Dari Tanggal", datetime.date.today() - datetime.timedelta(days=7))
            tgl_akhir = st.date_input("Sampai Tanggal", datetime.date.today())
        with col_f2:
            f_periode = st.multiselect("Filter Periode Pekerjaan", ["Harian", "Mingguan", "Bulanan"], default=["Harian", "Mingguan", "Bulanan"])
        
        # Proses Filter Data
        mask = (df['Tanggal'] >= tgl_awal) & (df['Tanggal'] <= tgl_akhir) & (df['periode'].isin(f_periode))
        df_f = df[mask].copy()
        
        st.write(f"Menampilkan {len(df_f)} data ditemukan.")
        st.dataframe(df_f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'keterangan', 'Tanggal']], use_container_width=True)
        
        # Tombol Download
        col_p1, col_p2 = st.columns(2)
        with col_p1: n_bi = st.selectbox("Mengetahui (BI)", list_peg)
        with col_p2: n_tk = st.selectbox("Dibuat (ME)", list_tek)
        
        if not df_f.empty:
            pdf_data = generate_pdf(df_f, f"{tgl_awal} s/d {tgl_akhir}", n_bi, n_tk)
            st.download_button(f"📥 DOWNLOAD PDF ({', '.join(f_periode)})", pdf_data, f"Laporan_ME_{tgl_awal}_{tgl_akhir}.pdf")
        else:
            st.warning("Data tidak ditemukan untuk filter ini.")
    else:
        st.info("Belum ada data di database.")