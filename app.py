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

# --- 2. CSS STABIL (Tampilan Menu Tetap Solid) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background: #0f172a; }
    .main-header { text-align: center; padding: 20px; background: #1e293b; border-bottom: 3px solid #38bdf8; margin-bottom: 20px; border-radius: 0 0 15px 15px; }
    .main-header h1 { color: white; margin: 0; font-size: 1.5rem; text-shadow: 0 0 10px #38bdf8; }
    div.stButton > button { width: 100%; height: 90px !important; background: #1e293b !important; border: 2px solid #334155 !important; border-radius: 12px !important; color: #38bdf8 !important; font-weight: bold !important; margin-bottom: 10px; }
    div.stButton > button:hover { border-color: #38bdf8 !important; box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
    label { color: #38bdf8 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIKA SOW DINAMIS ---
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

# --- 4. FUNGSI GENERATE PDF (PERBAIKAN TOTAL) ---
def generate_pdf(df, rentang_tgl, p_sel, t_sel):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Header Laporan
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "LAPORAN PEMELIHARAAN ME - BI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 7, f"Periode Laporan: {rentang_tgl}", ln=True, align="C")
    pdf.ln(10)
    
    # Tabel Header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(56, 189, 248) # Warna Biru Muda BI
    pdf.set_text_color(255, 255, 255)
    
    # Lebar Kolom
    w_nama = 50
    w_per = 25
    w_tek = 30
    w_kon = 30
    w_sow = 142

    pdf.cell(w_nama, 10, "Nama Aset", 1, 0, "C", True)
    pdf.cell(w_per, 10, "Periode", 1, 0, "C", True)
    pdf.cell(w_tek, 10, "Teknisi", 1, 0, "C", True)
    pdf.cell(w_kon, 10, "Kondisi", 1, 0, "C", True)
    pdf.cell(w_sow, 10, "Detail Pengecekan SOW & Keterangan", 1, 1, "C", True)
    
    # Isi Tabel
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)
    
    for _, row in df.iterrows():
        # Parsing SOW JSON
        sow = row.get('checklist_data', {})
        sow_txt = " | ".join([f"{k.replace('_',' ').title()}: {v}" for k, v in sow.items()]) if isinstance(sow, dict) else ""
        full_txt = f"{sow_txt}\nCatatan: {row['keterangan']}"
        
        # Hitung tinggi baris otomatis berdasarkan teks terpanjang
        current_y = pdf.get_y()
        if current_y > 170: # Auto Page Break jika hampir habis
            pdf.add_page()
            current_y = pdf.get_y()

        # Render kolom statis
        pdf.multi_cell(w_nama, 8, str(row['Nama Aset']), 1, "L")
        h = pdf.get_y() - current_y
        
        pdf.set_xy(w_nama + 10, current_y)
        pdf.cell(w_per, h, str(row.get('periode', '-')), 1, 0, "C")
        pdf.cell(w_tek, h, str(row['teknisi']), 1, 0, "C")
        pdf.cell(w_kon, h, str(row['kondisi']), 1, 0, "C")
        
        # Render Detail SOW dengan MultiCell (Bungkus Teks)
        pdf.multi_cell(w_sow, 8, full_txt, 1, "L")
        
    pdf.ln(15)
    
    # Tanda Tangan
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(140, 5, "Mengetahui,", 0, 0, "C")
    pdf.cell(140, 5, "Dibuat Oleh,", 0, 1, "C")
    pdf.ln(15)
    pdf.cell(140, 5, f"( {p_sel} )", 0, 0, "C")
    pdf.cell(140, 5, f"( {t_sel} )", 0, 1, "C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(140, 5, "Staf BI Balikpapan", 0, 0, "C")
    pdf.cell(140, 5, "Teknisi ME", 0, 1, "C")
    
    return bytes(pdf.output())

# --- 5. LOGIKA NAVIGASI ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
def pindah(nama): st.session_state.hal = nama

@st.cache_data(ttl=60)
def get_assets(): return supabase.table("assets").select("*").order("nama_aset").execute().data
@st.cache_data(ttl=60)
def get_staff(): return supabase.table("staff_me").select("*").execute().data
@st.cache_data(ttl=60)
def get_all_logs(): return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

assets_data = get_assets()
opt_asset = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in assets_data}
staff_data = get_staff()
list_tek = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_data if s['kategori'] == 'PEGAWAI']

st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI BALIKPAPAN</h1></div>', unsafe_allow_html=True)

# --- 6. ROUTING HALAMAN ---
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

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    curr = st.session_state.hal
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"Form Checklist {curr}")
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
            st.success("Tersimpan!"); st.balloons()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Monitoring & Export PDF")
    logs = get_all_logs()
    if logs:
        df = pd.DataFrame(logs)
        df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
        df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
        
        # Filter Periode & Tanggal
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            tgl_range = st.date_input("Pilih Rentang Tanggal", [datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()])
        with c_f2:
            f_per = st.multiselect("Filter Periode", ["Harian", "Mingguan", "Bulanan"], default=["Harian", "Mingguan", "Bulanan"])
            
        if len(tgl_range) == 2:
            mask = (df['Tanggal'] >= tgl_range[0]) & (df['Tanggal'] <= tgl_range[1]) & (df['periode'].isin(f_per))
            df_f = df[mask].copy()
            st.dataframe(df_f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'Tanggal']], use_container_width=True)
            
            n_bi = st.selectbox("Mengetahui (Staf BI)", list_peg)
            n_tk = st.selectbox("Dibuat (Teknisi ME)", list_tek)
            
            if st.download_button("📥 DOWNLOAD PDF LAPORAN", generate_pdf(df_f, f"{tgl_range[0]} s/d {tgl_range[1]}", n_bi, n_tk), f"Laporan_ME_{tgl_range[0]}.pdf"):
                st.success("Download Berhasil!")

# (Modul Lapor Gangguan & Update Perbaikan disingkat untuk menghemat ruang, gunakan yang lama jika sudah jalan)