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

# --- 2. CSS CYBER NEON (FIX BUTTON & LAYOUT) ---
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
    .main-header h1 { color: #f8fafc; text-shadow: 0 0 12px #38bdf8; margin: 0; font-size: 2.2rem; }

    /* Container Kartu Menu Utama */
    .menu-wrapper {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 180px;
        width: 100%;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(56, 189, 248, 0.2);
        transition: 0.3s;
        margin-bottom: 25px;
        overflow: hidden;
    }

    /* Memaksa Tombol Menutupi Seluruh Kartu agar Ikon Bisa Diklik */
    div.stButton > button {
        position: absolute;
        top: 0; left: 0;
        width: 100% !important;
        height: 180px !important;
        background-color: transparent !important;
        color: transparent !important; 
        border: none !important;
        z-index: 10;
        cursor: pointer;
    }

    .menu-wrapper:hover {
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid #38bdf8;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
        transform: translateY(-5px);
    }

    /* Konten di Dalam Kartu */
    .btn-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        z-index: 1;
    }
    .btn-text {
        font-weight: 700; color: #38bdf8; font-size: 0.85rem;
        margin-top: 15px; letter-spacing: 1px;
        text-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
        text-transform: uppercase;
        text-align: center;
    }

    /* Styling Form Input */
    label { color: #38bdf8 !important; font-weight: bold !important; }
    .stSelectbox, .stTextInput, .stTextArea, .stRadio { color: white !important; }
    .stMarkdown p { color: #cbd5e1; }
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

def render_sow(nama):
    st.info(f"📋 Parameter SOW: {nama}")
    ck = {}
    if "AC" in nama:
        ck['Filter'] = st.radio("Filter/Evap", ["Bersih", "Kotor"])
        ck['Drainase'] = st.radio("Drainase", ["Lancar", "Sumbat"])
    elif "Genset" in nama:
        ck['Oli'] = st.radio("Level Oli", ["Cukup", "Kurang"])
        ck['Accu'] = st.radio("Tegangan Accu", ["Normal", "Lemah"])
    elif "Chiller" in nama:
        ck['Arus'] = st.text_input("Arus (Ampere)")
        ck['Valve'] = st.radio("Kondisi Valve", ["OK", "Rusak"])
    else:
        ck['Fisik'] = st.radio("Kondisi Fisik", ["OK", "Bermasalah"])
    return ck

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
st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI</h1><p style="color:#38bdf8; letter-spacing:2px; font-size:0.8rem;">INTEGRATED DIGITAL MAINTENANCE</p></div>', unsafe_allow_html=True)

# --- 7. LOGIKA HALAMAN ---
if st.session_state.halaman == 'Menu Utama':
    _, col_menu, _ = st.columns([0.05, 0.9, 0.05])
    with col_menu:
        m1, m2 = st.columns(2)
        with m1:
            st.markdown('<div class="menu-wrapper"><div class="btn-content"><img src="https://img.icons8.com/neon/96/checklist.png" width="70"><div class="btn-text">Checklist Rutin</div></div>', unsafe_allow_html=True)
            if st.button(" ", key="m1"): ganti_hal('Rutin'); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="menu-wrapper"><div class="btn-content"><img src="https://img.icons8.com/neon/96/refresh.png" width="70"><div class="btn-text">Update Perbaikan</div></div>', unsafe_allow_html=True)
            if st.button(" ", key="m2"): ganti_hal('Update'); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with m2:
            st.markdown('<div class="menu-wrapper"><div class="btn-content"><img src="https://img.icons8.com/neon/96/error.png" width="70"><div class="btn-text">Lapor Gangguan</div></div>', unsafe_allow_html=True)
            if st.button(" ", key="m3"): ganti_hal('Gangguan'); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="menu-wrapper"><div class="btn-content"><img src="https://img.icons8.com/neon/96/combo-chart.png" width="70"><div class="btn-text">Dashboard & PDF</div></div>', unsafe_allow_html=True)
            if st.button(" ", key="m4"): ganti_hal('Export'); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

else:
    if st.button("⬅️ KEMBALI KE MENU UTAMA"): ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    # MODUL 1: CHECKLIST RUTIN
    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Form Checklist Rutin")
        sel = st.selectbox("Pilih Aset", list(opt_asset.keys()))
        aset = opt_asset[sel]
        with st.form("f_rutin", clear_on_submit=True):
            t = st.selectbox("Teknisi", list_tek)
            sow_res = render_sow(aset['nama_aset'])
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
                supabase.table("maintenance_logs").insert({"asset_id": aset['id'], "teknisi": t, "kondisi": kon, "keterangan": ket, "foto_url": url, "checklist_data": sow_res}).execute()
                st.success("Berhasil Disimpan!"); st.balloons()

    # MODUL 2: LAPOR GANGGUAN
    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Lapor Kerusakan")
        sel_g = st.selectbox("Aset Bermasalah", list(opt_asset.keys()))
        aset_g = opt_asset[sel_g]
        with st.form("f_gng", clear_on_submit=True):
            pel = st.selectbox("Pelapor", list_tek)
            mas = st.text_area("Deskripsi Kerusakan")
            urg = st.select_slider("Urgensi", ["Rendah", "Sedang", "Darurat"], value="Sedang")
            pake_cam_g = st.checkbox("📸 Aktifkan Kamera")
            foto_g = st.camera_input("Foto") if pake_cam_g else None
            if st.form_submit_button("KIRIM LAPORAN"):
                url_g = None
                if foto_g:
                    fn_g = f"G_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_g, foto_g.getvalue())
                    url_g = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_g)
                supabase.table("gangguan_logs").insert({"asset_id": aset_g['id'], "teknisi": pel, "masalah": mas, "urgensi": urg, "status": "Open", "foto_kerusakan_url": url_g}).execute()
                st.error("Laporan Terkirim!")

    # MODUL 3: UPDATE PERBAIKAN
    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Update Penyelesaian")
        iss = get_open_issues()
        if not iss: st.info("Tidak ada gangguan aktif.")
        else:
            iss_opt = {f"[{i['urgensi']}] {i['assets']['nama_aset']} - {i['masalah'][:30]}": i for i in iss}
            sel_i = st.selectbox("Pilih Gangguan", list(iss_opt.keys()))
            dat_i = iss_opt[sel_i]
            with st.form("f_fix"):
                tp = st.selectbox("Teknisi Pelaksana", list_tek)
                tin = st.text_area("Tindakan Perbaikan")
                pake_cam_f = st.checkbox("📸 Aktifkan Kamera (After)")
                f_a = st.camera_input("Foto After") if pake_cam_f else None
                if st.form_submit_button("SELESAI / RESOLVED"):
                    url_a = None
                    if f_a:
                        fn_a = f"F_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_a, f_a.getvalue())
                        url_a = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_a)
                    supabase.table("gangguan_logs").update({"status": "Resolved", "tindakan_perbaikan": tin, "teknisi_perbaikan": tp, "tgl_perbaikan": datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url": url_a}).eq("id", dat_i['id']).execute()
                    st.success("Status Berhasil Diupdate!")

    # MODUL 4: DASHBOARD & EXPORT PDF
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
                for k in ["OK", "Bersih", "Lancar", "Normal", "Cukup", "Ya"]: df_fin = df_fin.replace(k, "v")
                st.dataframe(df_fin.fillna("-"), use_container_width=True)
                
                n_bi = st.selectbox("Mengetahui (BI)", list_peg)
                n_tk = st.selectbox("Dibuat (ME)", list_tek)
                if st.download_button("📥 DOWNLOAD PDF", generate_pdf(df_fin.fillna("-"), dp, n_bi, n_tk), f"Lap_{dp}.pdf", "application/pdf"):
                    st.success("PDF Diunduh")
            else: st.warning("Data kosong pada tanggal ini.")