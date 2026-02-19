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

# --- 2. CSS CUSTOM ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background: #0f172a; }
    .main-header { text-align: center; padding: 20px; background: #1e293b; border-bottom: 3px solid #00adef; margin-bottom: 20px; border-radius: 0 0 15px 15px; }
    .main-header h1 { color: white; margin: 0; font-size: 1.5rem; text-shadow: 0 0 10px #00adef; }
    div.stButton > button { width: 100%; height: 80px !important; background: #1e293b !important; border: 2px solid #334155 !important; border-radius: 12px !important; color: #00adef !important; font-weight: bold !important; margin-bottom: 10px; }
    div.stButton > button:hover { border-color: #00adef !important; box-shadow: 0 0 15px rgba(0, 173, 239, 0.3); }
    label { color: #00adef !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI LOGIKA SOW ---
def get_sow_fields(nama_aset, jenis):
    fields = {}
    st.write(f"### 📋 Parameter {jenis}")
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

# --- 4. FUNGSI GENERATE PDF (FORMAT TTD FIX) ---
def generate_pdf(df, rentang_tgl, peg_data, tek_data):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "LAPORAN PEMELIHARAAN ME - BI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 7, f"Periode: {rentang_tgl}", ln=True, align="C")
    pdf.ln(10)
    
    # Header Tabel
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(0, 173, 239)
    pdf.set_text_color(255, 255, 255)
    
    w = [55, 25, 35, 35, 127]
    cols = ["Aset", "Periode", "Teknisi", "Kondisi", "Detail SOW & Keterangan"]
    for i in range(len(cols)):
        pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
    pdf.ln()

    # Isi Tabel
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)
    
    for _, row in df.iterrows():
        sow_data = row.get('checklist_data', {})
        if isinstance(sow_data, str):
            try: sow_data = json.loads(sow_data)
            except: sow_data = {}
        
        sow_txt = " | ".join([f"{k.replace('_',' ').capitalize()}: {v}" for k, v in sow_data.items()])
        full_ket = f"{sow_txt}\nCatatan: {row['keterangan']}"
        
        start_y = pdf.get_y()
        pdf.multi_cell(w[0], 10, str(row['Nama Aset']), 1, 'L')
        y_aset = pdf.get_y()
        
        pdf.set_xy(10 + w[0] + w[1] + w[2] + w[3], start_y)
        pdf.multi_cell(w[4], 5, full_ket, 1, 'L')
        y_detail = pdf.get_y()
        
        max_h = max(y_aset, y_detail) - start_y
        
        # Draw Borders
        pdf.rect(10, start_y, w[0], max_h)
        pdf.rect(10+w[0], start_y, w[1], max_h)
        pdf.rect(10+w[0]+w[1], start_y, w[2], max_h)
        pdf.rect(10+w[0]+w[1]+w[2], start_y, w[3], max_h)
        
        # Center Cells
        pdf.set_xy(10+w[0], start_y)
        pdf.cell(w[1], max_h, str(row.get('periode', '-')), 0, 0, "C")
        pdf.cell(w[2], max_h, str(row['teknisi']), 0, 0, "C")
        pdf.cell(w[3], max_h, str(row['kondisi']), 0, 0, "C")
        
        pdf.set_y(start_y + max_h)
        if pdf.get_y() > 170: pdf.add_page()

    # --- TANDA TANGAN ---
    pdf.ln(15)
    cur_y = pdf.get_y()
    pdf.set_font("Helvetica", "", 10)
    
    # Baris 1: Judul
    pdf.set_xy(10, cur_y)
    pdf.cell(138, 5, "Diketahui,", 0, 0, "C")
    pdf.set_xy(148, cur_y)
    pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
    
    # Baris 2: Posisi / Nama CV
    pdf.cell(138, 5, peg_data.get('posisi', ''), 0, 0, "C")
    pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
    
    pdf.ln(18)
    
    # Baris 3: Nama (Garis Bawah)
    pdf.set_font("Helvetica", "BU", 10)
    pdf.cell(138, 5, peg_data.get('nama', ''), 0, 0, "C")
    pdf.cell(138, 5, tek_data.get('nama', ''), 0, 1, "C")
    
    # Baris 4: Jabatan_pdf / Teknisi ME
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(138, 5, peg_data.get('jabatan_pdf', ''), 0, 0, "C")
    pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")

    return bytes(pdf.output())

# --- 5. DATA & NAVIGASI ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
def pindah(n): st.session_state.hal = n

@st.cache_data(ttl=30)
def load_data():
    a = supabase.table("assets").select("*").order("nama_aset").execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
staff_map = {s['nama']: s for s in staff_list}
opt_asset = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in assets_list}
list_tek = [s['nama'] for s in staff_list if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_list if s['kategori'] == 'PEGAWAI']

st.markdown(f'<div class="main-header"><h1>⚡ SIMANTAP BI BALIKPAPAN</h1></div>', unsafe_allow_html=True)

if st.session_state.hal == 'Menu':
    c1, c2 = st.columns(2)
    with c1:
        if st.button("☀️\nCHECKLIST HARIAN"): pindah('Harian'); st.rerun()
        if st.button("📅\nCHECKLIST MINGGUAN"): pindah('Mingguan'); st.rerun()
        if st.button("🏆\nCHECKLIST BULANAN"): pindah('Bulanan'); st.rerun()
    with c2:
        if st.button("⚠️\nLAPOR GANGGUAN"): pindah('Gangguan'); st.rerun()
        if st.button("🔄\nUPDATE PERBAIKAN"): pindah('Update'); st.rerun()
        if st.button("📊\nDASHBOARD & PDF"): pindah('Export'); st.rerun()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Monitoring & Export PDF")
    logs = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
    if logs:
        df = pd.DataFrame(logs)
        df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
        df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
        
        c_t, c_p = st.columns(2)
        with c_t: tgl_r = st.date_input("Rentang Tanggal", [datetime.date.today(), datetime.date.today()])
        with c_p: per_f = st.multiselect("Periode", ["Harian", "Mingguan", "Bulanan"], default=["Harian", "Mingguan", "Bulanan"])
        
        if len(tgl_r) == 2:
            mask = (df['Tanggal'] >= tgl_r[0]) & (df['Tanggal'] <= tgl_r[1]) & (df['periode'].isin(per_f))
            df_f = df[mask]
            st.dataframe(df_f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'Tanggal']], use_container_width=True)
            
            p_sel = st.selectbox("Diketahui (BI)", list_peg)
            t_sel = st.selectbox("Dibuat (Teknisi)", list_tek)
            
            if st.download_button("📥 DOWNLOAD PDF", generate_pdf(df_f, f"{tgl_r[0]} s/d {tgl_r[1]}", staff_map[p_sel], staff_map[t_sel]), f"Lap_ME.pdf"):
                st.success("Download Berhasil!")

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    curr = st.session_state.hal
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"Form {curr}")
    sel_a = st.selectbox("Pilih Aset", list(opt_asset.keys()))
    with st.form("f_run", clear_on_submit=True):
        t = st.selectbox("Teknisi", list_tek)
        res_sow = get_sow_fields(opt_asset[sel_a]['nama_aset'], curr)
        kon = st.radio("Kondisi", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
        ket = st.text_area("Keterangan")
        if st.form_submit_button("SIMPAN"):
            supabase.table("maintenance_logs").insert({"asset_id": opt_asset[sel_a]['id'], "teknisi": t, "periode": curr, "checklist_data": res_sow, "kondisi": kon, "keterangan": ket}).execute()
            st.success("Berhasil!"); st.balloons()

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("⚠️ Lapor Gangguan")
    sel_g = st.selectbox("Aset", list(opt_asset.keys()))
    with st.form("f_g"):
        masalah = st.text_area("Masalah")
        if st.form_submit_button("KIRIM"):
            supabase.table("gangguan_logs").insert({"asset_id": opt_asset[sel_g]['id'], "masalah": masalah, "status": "Open"}).execute()
            st.error("Laporan Dikirim")