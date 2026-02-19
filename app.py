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

# --- 2. CSS NEON CYBER UI (PAMUNGKAS) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background: radial-gradient(circle, #0f172a 0%, #020617 100%); }
    
    .main-header {
        text-align: center; padding: 30px;
        background: rgba(30, 58, 138, 0.1);
        border-bottom: 2px solid #38bdf8;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
        margin-bottom: 40px;
    }
    .main-header h1 { color: #f8fafc; font-size: 2.5rem; text-shadow: 0 0 10px #38bdf8; }
    
    div.stButton > button {
        width: 100%; height: 180px !important;
        border-radius: 20px !important;
        background: rgba(255, 255, 255, 0.03) !important;
        color: transparent !important; /* Menghilangkan teks asli button */
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        transition: 0.4s ease;
    }
    div.stButton > button:hover {
        background: rgba(56, 189, 248, 0.1) !important;
        border: 1px solid #38bdf8 !important;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.4) !important;
        transform: translateY(-5px);
    }
    .btn-text {
        font-weight: 700; color: #38bdf8; font-size: 0.9rem;
        margin-top: 15px; letter-spacing: 2px;
    }
    /* Input Form agar kontras di latar gelap */
    .stTextInput, .stSelectbox, .stTextArea, .stRadio { color: white !important; }
    label { color: #38bdf8 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI LOGIKA (DATABASE & PDF) ---
@st.cache_data(ttl=60)
def get_assets(): return supabase.table("assets").select("*").order("nama_aset").execute().data

def get_open_issues(): return supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute().data

def get_all_logs(): return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

def get_staff(): return supabase.table("staff_me").select("*").execute().data

def generate_pdf(df, tgl, p_sel, t_sel):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "LAPORAN MAINTENANCE ME - BI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"Tanggal: {tgl}", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(200, 230, 255)
    pdf.cell(60, 8, "Nama Aset", 1, 0, "C", True)
    pdf.cell(30, 8, "Teknisi", 1, 0, "C", True)
    pdf.cell(30, 8, "Kondisi", 1, 0, "C", True)
    pdf.cell(155, 8, "SOW Detail", 1, 1, "C", True)
    pdf.set_font("Helvetica", "", 7)
    for _, row in df.iterrows():
        exclude = ['Nama Aset', 'teknisi', 'kondisi', 'keterangan', 'Tanggal']
        sow = ", ".join([str(k) for k, v in row.items() if k not in exclude and v == "v"])
        pdf.cell(60, 7, str(row['Nama Aset']), 1)
        pdf.cell(30, 7, str(row['teknisi']), 1, 0, "C")
        pdf.cell(30, 7, str(row['kondisi']), 1, 0, "C")
        pdf.cell(155, 7, sow[:110], 1, 1)
    return bytes(pdf.output())

def render_sow(nama):
    st.markdown(f"### ⚙️ Parameter: {nama}")
    ck = {}
    if "AC" in nama:
        ck['Filter'] = st.radio("Filter/Evap", ["Bersih", "Kotor"])
        ck['Drainase'] = st.radio("Drainase", ["Lancar", "Sumbat"])
    elif "Chiller" in nama:
        ck['Freon'] = st.radio("Tekanan Freon", ["Normal", "Rendah"])
        ck['Amper'] = st.text_input("Arus (Ampere)")
    else:
        ck['Cek_Fisik'] = st.radio("Kondisi Fisik", ["OK", "Bermasalah"])
    return ck

# --- 4. NAVIGASI ---
if 'halaman' not in st.session_state: st.session_state.halaman = 'Menu Utama'
def ganti_hal(nama): st.session_state.halaman = nama

# --- 5. HEADER ---
st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI</h1><p style="color:#38bdf8">INTEGRATED DIGITAL MAINTENANCE</p></div>', unsafe_allow_html=True)

# --- 6. LOGIKA HALAMAN ---
asset_data = get_assets()
opt_asset = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}
staff_data = get_staff()
list_tek = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']

if st.session_state.halaman == 'Menu Utama':
    _, col_p, _ = st.columns([0.1, 0.8, 0.1])
    with col_p:
        m1, m2 = st.columns(2)
        with m1:
            if st.button(" ", key="btn1"): ganti_hal('Rutin'); st.rerun()
            st.markdown('<div style="margin-top:-160px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/checklist.png" width="70"><div class="btn-text">CHECKLIST RUTIN</div></div><br>', unsafe_allow_html=True)
            
            if st.button(" ", key="btn2"): ganti_hal('Update'); st.rerun()
            st.markdown('<div style="margin-top:-160px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/refresh.png" width="70"><div class="btn-text">UPDATE PERBAIKAN</div></div><br>', unsafe_allow_html=True)
        with m2:
            if st.button(" ", key="btn3"): ganti_hal('Gangguan'); st.rerun()
            st.markdown('<div style="margin-top:-160px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/error.png" width="70"><div class="btn-text">LAPOR GANGGUAN</div></div><br>', unsafe_allow_html=True)
            
            if st.button(" ", key="btn4"): ganti_hal('Export'); st.rerun()
            st.markdown('<div style="margin-top:-160px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/combo-chart.png" width="70"><div class="btn-text">DASHBOARD & PDF</div></div><br>', unsafe_allow_html=True)

else:
    if st.button("⬅️ KEMBALI KE MENU"): ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Form Pemeliharaan Rutin")
        sel = st.selectbox("Pilih Aset", list(opt_asset.keys()))
        aset = opt_asset[sel]
        with st.form("f_rutin"):
            t = st.selectbox("Teknisi", list_tek)
            sow_res = render_sow(aset['nama_aset'])
            kon = st.radio("Kondisi", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
            ket = st.text_area("Keterangan")
            foto = st.camera_input("Foto")
            if st.form_submit_button("SIMPAN"):
                url = None
                if foto:
                    fn = f"R_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                    url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
                supabase.table("maintenance_logs").insert({"asset_id": aset['id'], "teknisi": t, "kondisi": kon, "keterangan": ket, "foto_url": url, "checklist_data": sow_res}).execute()
                st.success("Tersimpan!"); st.balloons()

    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Lapor Gangguan")
        sel_g = st.selectbox("Aset", list(opt_asset.keys()))
        aset_g = opt_asset[sel_g]
        with st.form("f_gng"):
            pel = st.selectbox("Pelapor", list_tek)
            mas = st.text_area("Masalah")
            urg = st.select_slider("Urgensi", ["Rendah", "Sedang", "Darurat"])
            foto_g = st.camera_input("Foto")
            if st.form_submit_button("KIRIM"):
                url_g = None
                if foto_g:
                    fn_g = f"G_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_g, foto_g.getvalue())
                    url_g = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_g)
                supabase.table("gangguan_logs").insert({"asset_id": aset_g['id'], "teknisi": pel, "masalah": mas, "urgensi": urg, "status": "Open", "foto_kerusakan_url": url_g}).execute()
                st.error("Laporan Dikirim!")

    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Update Perbaikan")
        iss = get_open_issues()
        if not iss: st.info("Tidak ada gangguan aktif.")
        else:
            iss_opt = {f"[{i['urgensi']}] {i['assets']['nama_aset']}": i for i in iss}
            sel_i = st.selectbox("Pilih Gangguan", list(iss_opt.keys()))
            dat_i = iss_opt[sel_i]
            with st.form("f_fix"):
                tp = st.selectbox("Teknisi", list_tek)
                tin = st.text_area("Tindakan")
                f_a = st.camera_input("Foto After")
                if st.form_submit_button("SELESAI"):
                    url_a = None
                    if f_a:
                        fn_a = f"F_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_a, f_a.getvalue())
                        url_a = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_a)
                    supabase.table("gangguan_logs").update({"status": "Resolved", "tindakan_perbaikan": tin, "teknisi_perbaikan": tp, "tgl_perbaikan": datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url": url_a}).eq("id", dat_i['id']).execute()
                    st.success("Berhasil diupdate!")

    elif st.session_state.halaman == 'Export':
        st.subheader("📊 Monitoring & PDF")
        logs = get_all_logs()
        if logs:
            df = pd.DataFrame(logs)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'])
            df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
            st.metric("Total Laporan", len(df))
            dp = st.date_input("Filter Tanggal", datetime.date.today())
            df_f = df[df['Tanggal'] == dp].copy()
            if not df_f.empty:
                c_df = pd.json_normalize(df_f['checklist_data'])
                df_fin = pd.concat([df_f[['Nama Aset', 'teknisi', 'kondisi']].reset_index(drop=True), c_df.reset_index(drop=True)], axis=1)
                for k in ["OK", "Bersih", "Lancar", "Normal"]: df_fin = df_fin.replace(k, "v")
                st.dataframe(df_fin.fillna("-"))
                
                staff_bi = [s for s in staff_data if s['kategori'] == 'PEGAWAI']
                n_bi = st.selectbox("Mengetahui (BI)", [s['nama'] for s in staff_bi])
                n_tk = st.selectbox("Dibuat (ME)", list_tek)
                
                pdf_res = generate_pdf(df_fin.fillna("-"), dp, {"nama": n_bi}, {"nama": n_tk})
                st.download_button("📥 DOWNLOAD PDF", pdf_res, f"Lap_{dp}.pdf", "application/pdf")