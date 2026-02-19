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

# --- 2. CUSTOM CSS (TAMPILAN MEWAH) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .main-header {
        text-align: center;
        padding: 25px;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        border-radius: 0 0 30px 30px;
        margin-bottom: 20px;
    }
    div.stButton > button {
        width: 100%;
        height: 150px !important;
        border-radius: 20px !important;
        background-color: white !important;
        color: #1E3A8A !important;
        font-weight: bold !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        transition: 0.3s;
        border: 1px solid #eee !important;
    }
    div.stButton > button:hover {
        transform: translateY(-5px) !important;
        border: 1px solid #3B82F6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI-FUNGSI LOGIKA ---
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
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "CHECKLIST HARIAN TEKNISI ME - KPwBI BALIKPAPAN", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(60, 8, "Nama Aset", border=1, fill=True)
    pdf.cell(35, 8, "Teknisi", border=1, fill=True)
    pdf.cell(35, 8, "Kondisi", border=1, fill=True)
    pdf.cell(147, 8, "Detail Parameter SOW", border=1, fill=True, ln=True)
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        exclude = ['Nama Aset', 'teknisi', 'kondisi', 'keterangan', 'Tanggal']
        params = [f"{k}" for k, v in row.items() if k not in exclude and v == "v"]
        pdf.cell(60, 7, str(row['Nama Aset'])[:40], border=1)
        pdf.cell(35, 7, str(row['teknisi']), border=1)
        pdf.cell(35, 7, str(row['kondisi']), border=1)
        pdf.cell(147, 7, ", ".join(params)[:110] if params else "-", border=1, ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(138, 5, "Diketahui,", 0, 0, "C")
    pdf.cell(138, 5, "Dibuat Oleh,", 0, 1, "C")
    pdf.ln(10)
    pdf.cell(138, 5, f"{p_sel['nama']}", 0, 0, "C")
    pdf.cell(138, 5, f"{t_sel['nama']}", 0, 1, "C")
    return bytes(pdf.output())

def render_sow_checklist(nama_unit):
    st.info(f"📋 Parameter SOW: {nama_unit}")
    ck = {}
    if "AC" in nama_unit:
        ck['Filter_Evap'] = st.radio("Filter & Evaporator", ["Bersih", "Kotor"])
        ck['Drainase'] = st.radio("Saluran Drainase", ["Lancar", "Tersumbat"])
    elif "Chiller" in nama_unit:
        ck['Listrik'] = st.radio("Sistem Kelistrikan", ["Normal", "Abnormal"])
        ck['Oli_Freon'] = st.radio("Oli & Freon", ["Ya", "Tidak"])
    else:
        ck['Catatan'] = st.text_area("Detail Pengecekan Umum")
    return ck

# --- 4. NAVIGASI ---
if 'halaman' not in st.session_state:
    st.session_state.halaman = 'Menu Utama'

def ganti_hal(nama_hal):
    st.session_state.halaman = nama_hal

# --- 5. HEADER ---
st.markdown('<div class="main-header"><h1>🚀 SIMANTAP BI BPP</h1><p>Digital Maintenance System</p></div>', unsafe_allow_html=True)

# --- 6. LOGIKA HALAMAN ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}
staff_all = get_staff_data()
list_tek = [s['nama'] for s in staff_all if s['kategori'] == 'TEKNISI']

if st.session_state.halaman == 'Menu Utama':
    _, col_menu, _ = st.columns([0.1, 0.8, 0.1])
    with col_menu:
        m1, m2 = st.columns(2)
        with m1:
            if st.button("📋\n\nCHECKLIST RUTIN"): ganti_hal('Rutin'); st.rerun()
            st.write("#")
            if st.button("✅\n\nUPDATE PERBAIKAN"): ganti_hal('Update'); st.rerun()
        with m2:
            if st.button("⚠️\n\nLAPOR GANGGUAN"): ganti_hal('Gangguan'); st.rerun()
            st.write("#")
            if st.button("📊\n\nDASHBOARD & PDF"): ganti_hal('Export'); st.rerun()

else:
    if st.button("⬅️ KEMBALI KE MENU"): ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    # MODUL 1: RUTIN
    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Checklist Rutin")
        sel_label = st.selectbox("Pilih Aset", options=list(options.keys()))
        asset = options[sel_label]
        with st.form("f_rutin"):
            tek = st.selectbox("Teknisi", options=list_tek)
            res = render_sow_checklist(asset['nama_aset'])
            kon = st.radio("Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
            ket = st.text_area("Keterangan")
            siap_cam = st.checkbox("📸 Aktifkan Kamera")
            foto = st.camera_input("Ambil Foto") if siap_cam else None
            if st.form_submit_button("SIMPAN"):
                url = None
                if foto:
                    fn = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                    url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
                supabase.table("maintenance_logs").insert({"asset_id": asset['id'], "teknisi": tek, "kondisi": kon, "keterangan": ket, "foto_url": url, "checklist_data": res}).execute()
                st.success("Laporan Berhasil Disimpan!"); st.balloons()

    # MODUL 2: GANGGUAN
    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Lapor Gangguan")
        sel_g = st.selectbox("Aset Bermasalah", options=list(options.keys()))
        asset_g = options[sel_g]
        with st.form("f_gng"):
            pel = st.selectbox("Pelapor", options=list_tek)
            mas = st.text_area("Deskripsi Kerusakan")
            urg = st.select_slider("Urgensi", options=["Rendah", "Sedang", "Darurat"])
            siap_g = st.checkbox("📸 Aktifkan Kamera")
            foto_g = st.camera_input("Foto Kerusakan") if siap_g else None
            if st.form_submit_button("KIRIM LAPORAN"):
                url_g = None
                if foto_g:
                    fn_g = f"GNG_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_g, foto_g.getvalue())
                    url_g = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_g)
                supabase.table("gangguan_logs").insert({"asset_id": asset_g['id'], "teknisi": pel, "masalah": mas, "urgensi": urg, "status": "Open", "foto_kerusakan_url": url_g}).execute()
                st.error("Laporan Gangguan Terkirim!")

    # MODUL 3: UPDATE
    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Update Perbaikan")
        issues = get_open_issues()
        if not issues: st.info("Semua aset normal.")
        else:
            iss_opt = {f"[{i['urgensi']}] {i['assets']['nama_aset']}": i for i in issues}
            sel_i = st.selectbox("Pilih Laporan Selesai", list(iss_opt.keys()))
            dat_i = iss_opt[sel_i]
            with st.form("f_fix"):
                tek_p = st.selectbox("Teknisi Eksekutor", options=list_tek)
                tin = st.text_area("Tindakan")
                siap_f = st.checkbox("📸 Kamera")
                f_a = st.camera_input("Foto After") if siap_f else None
                if st.form_submit_button("SELESAI"):
                    url_a = None
                    if f_a:
                        fn_a = f"FIX_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_a, f_a.getvalue())
                        url_a = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_a)
                    supabase.table("gangguan_logs").update({"status": "Resolved", "tindakan_perbaikan": tin, "teknisi_perbaikan": tek_p, "tgl_perbaikan": datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url": url_a}).eq("id", dat_i['id']).execute()
                    st.success("Status Diupdate!")

    # MODUL 4: EXPORT
    elif st.session_state.halaman == 'Export':
        st.subheader("📊 Dashboard")
        logs = get_all_maintenance_logs()
        if logs:
            df = pd.DataFrame(logs)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'])
            df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
            st.metric("Total Laporan", len(df))
            d_p = st.date_input("Pilih Tanggal Laporan", datetime.date.today())
            df_f = df[df['Tanggal'] == d_p].copy()
            if not df_f.empty:
                c_df = pd.json_normalize(df_f['checklist_data'])
                df_fin = pd.concat([df_f[['Nama Aset', 'teknisi', 'kondisi', 'keterangan']].reset_index(drop=True), c_df.reset_index(drop=True)], axis=1)
                for k in ["Sudah", "Normal", "Baik", "Lancar", "Bersih", "Ya", "OK"]: df_fin = df_fin.replace(k, "v")
                st.dataframe(df_fin.fillna("-"))
                
                n_bi = st.selectbox("Pegawai BI", [s['nama'] for s in staff_all if s['kategori'] == 'PEGAWAI'])
                n_tk = st.selectbox("Teknisi Utama", list_tek)
                p_s = [s for s in staff_all if s['nama'] == n_bi][0]
                t_s = [s for s in staff_all if s['nama'] == n_tk][0]
                
                pdf_res = generate_pdf_simantap(df_fin.fillna("-"), d_p, p_s, t_s)
                st.download_button("📥 Download PDF", pdf_res, f"Laporan_{d_p}.pdf", "application/pdf")