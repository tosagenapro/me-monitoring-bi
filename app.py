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

# --- 2. CSS STABIL (Tampilan Mobile Friendly) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background: #0f172a; }
    .main-header { text-align: center; padding: 20px; background: #1e293b; border-bottom: 3px solid #38bdf8; margin-bottom: 20px; border-radius: 0 0 15px 15px; }
    .main-header h1 { color: white; margin: 0; font-size: 1.5rem; text-shadow: 0 0 10px #38bdf8; }
    div.stButton > button { width: 100%; height: 90px !important; background: #1e293b !important; border: 2px solid #334155 !important; border-radius: 12px !important; color: #38bdf8 !important; font-weight: bold !important; margin-bottom: 10px; }
    div.stButton > button:hover { border-color: #38bdf8 !important; box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
    label { color: #38bdf8 !important; font-weight: bold !important; }
    .stSelectbox, .stTextInput, .stTextArea { background-color: #1e293b !important; color: white !important; }
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

# --- 4. FUNGSI GENERATE PDF (FIX TOTAL - TIDAK AMBURADUL) ---
def generate_pdf(df, rentang_tgl, p_sel, t_sel):
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
    pdf.set_fill_color(56, 189, 248) # Biru Terang
    pdf.set_text_color(255, 255, 255)
    
    cols = {"Aset": 55, "Periode": 25, "Teknisi": 35, "Kondisi": 35, "Detail SOW & Keterangan": 127}
    for txt, w in cols.items():
        pdf.cell(w, 10, txt, 1, 0, "C", True)
    pdf.ln()

    # Isi Tabel
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)
    
    for _, row in df.iterrows():
        # Gabungkan data SOW JSON ke Teks
        sow_data = row.get('checklist_data', {})
        if isinstance(sow_data, str):
            try: sow_data = json.loads(sow_data)
            except: sow_data = {}
        
        sow_txt = " | ".join([f"{k.replace('_',' ').capitalize()}: {v}" for k, v in sow_data.items()])
        full_ket = f"{sow_txt}\nCatatan: {row['keterangan']}"
        
        # Hitung baris agar kotak tidak pecah (MultiCell logic)
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        
        # Kolom Nama Aset (Bisa wrap)
        pdf.multi_cell(55, 10, str(row['Nama Aset']), 1, 'L')
        end_y = pdf.get_y()
        row_height = end_y - start_y
        
        # Pindah ke samping untuk kolom lainnya dengan tinggi yang sama
        pdf.set_xy(start_x + 55, start_y)
        pdf.cell(25, row_height, str(row.get('periode', '-')), 1, 0, "C")
        pdf.cell(35, row_height, str(row['teknisi']), 1, 0, "C")
        pdf.cell(35, row_height, str(row['kondisi']), 1, 0, "C")
        
        # Kolom Detail (Wrap text)
        pdf.multi_cell(127, 5, full_ket, 1, 'L')
        
        # Reset posisi untuk baris baru agar tidak menumpuk
        if pdf.get_y() < end_y:
            pdf.set_y(end_y)
        pdf.ln(0)

    # Footer Tanda Tangan
    pdf.ln(15)
    y_sign = pdf.get_y()
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(40, y_sign); pdf.cell(0, 5, "Mengetahui,")
    pdf.set_xy(210, y_sign); pdf.cell(0, 5, "Dibuat Oleh,")
    
    pdf.ln(20)
    pdf.set_font("Helvetica", "BU", 10)
    pdf.set_xy(40, pdf.get_y()); pdf.cell(0, 5, f"( {p_sel} )")
    pdf.set_xy(210, pdf.get_y()); pdf.cell(0, 5, f"( {t_sel} )")
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(40, pdf.get_y()); pdf.cell(0, 5, "Staf BI Balikpapan")
    pdf.set_xy(210, pdf.get_y()); pdf.cell(0, 5, "Teknisi ME")

    return bytes(pdf.output())

# --- 5. LOGIKA DATA & NAVIGASI ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
def pindah(nama): st.session_state.hal = nama

@st.cache_data(ttl=30)
def load_data():
    a = supabase.table("assets").select("*").order("nama_aset").execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
opt_asset = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in assets_list}
list_tek = [s['nama'] for s in staff_list if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_list if s['kategori'] == 'PEGAWAI']

# --- 6. TAMPILAN ---
st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI BALIKPAPAN</h1></div>', unsafe_allow_html=True)

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
    st.subheader(f"Form {curr}")
    sel_a = st.selectbox("Pilih Aset", list(opt_asset.keys()))
    with st.form("f_run", clear_on_submit=True):
        t = st.selectbox("Teknisi", list_tek)
        res_sow = get_sow_fields(opt_asset[sel_a]['nama_aset'], curr)
        kon = st.radio("Kondisi", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
        ket = st.text_area("Keterangan")
        cam = st.checkbox("📸 Kamera")
        foto = st.camera_input("Foto") if cam else None
        if st.form_submit_button("SIMPAN"):
            url = None
            if foto:
                fn = f"{curr}_{datetime.datetime.now().strftime('%m%d_%H%M%S')}.jpg"
                supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
            supabase.table("maintenance_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "teknisi": t, "periode": curr,
                "checklist_data": res_sow, "kondisi": kon, "keterangan": ket, "foto_url": url
            }).execute()
            st.success("Berhasil!"); st.balloons()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Export Laporan PDF")
    all_logs = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
    if all_logs:
        df = pd.DataFrame(all_logs)
        df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
        df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
        
        c1, c2 = st.columns(2)
        with c1: tgls = st.date_input("Rentang Tanggal", [datetime.date.today(), datetime.date.today()])
        with c2: pers = st.multiselect("Periode", ["Harian", "Mingguan", "Bulanan"], default=["Harian", "Mingguan", "Bulanan"])
        
        if len(tgls) == 2:
            mask = (df['Tanggal'] >= tgls[0]) & (df['Tanggal'] <= tgls[1]) & (df['periode'].isin(pers))
            df_f = df[mask]
            st.dataframe(df_f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'Tanggal']], use_container_width=True)
            
            p_ttd = st.selectbox("Mengetahui (Staf BI)", list_peg)
            t_ttd = st.selectbox("Dibuat (Teknisi)", list_tek)
            
            if st.download_button("📥 DOWNLOAD PDF", generate_pdf(df_f, f"{tgls[0]} s/d {tgls[1]}", p_ttd, t_ttd), "Laporan_ME.pdf"):
                st.success("Selesai!")

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("⚠️ Lapor Gangguan")
    sel_g = st.selectbox("Aset", list(opt_asset.keys()))
    with st.form("f_g"):
        masalah = st.text_area("Masalah")
        if st.form_submit_button("KIRIM"):
            supabase.table("gangguan_logs").insert({"asset_id": opt_asset[sel_g]['id'], "masalah": masalah, "status": "Open"}).execute()
            st.error("Laporan Dikirim")

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("🔄 Update Status")
    st.info("Fitur ini menarik data dari Gangguan_Logs yang masih Open.")