import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF

# --- CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP BI BPP", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- CUSTOM CSS UNTUK TAMPILAN IKON ---
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 150px;
        border-radius: 20px;
        border: 2px solid #f0f2f6;
        background-color: #ffffff;
        color: #31333F;
        font-size: 20px;
        font-weight: bold;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        border-color: #007bff;
        color: #007bff;
        transform: translateY(-5px);
        box-shadow: 0px 8px 15px rgba(0,0,0,0.1);
    }
    .main-title {
        text-align: center;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-title {
        text-align: center;
        color: #6B7280;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NAVIGASI SESSION STATE ---
if 'halaman' not in st.session_state:
    st.session_state.halaman = 'Menu Utama'

def ganti_hal(nama_hal):
    st.session_state.halaman = nama_hal

# --- FUNGSI DATA & PDF (TETAP SAMA) ---
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
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "CHECKLIST HARIAN TEKNISI ME - KPwBI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Tanggal Pekerjaan: {tgl}", ln=True, align="C")
    pdf.ln(3); pdf.line(10, 26, 287, 26); pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(60, 8, "Nama Aset", border=1, fill=True, align="C")
    pdf.cell(35, 8, "Teknisi", border=1, fill=True, align="C")
    pdf.cell(35, 8, "Kondisi", border=1, fill=True, align="C")
    pdf.cell(147, 8, "Detail Parameter SOW", border=1, fill=True, align="C", ln=True)
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        exclude = ['Nama Aset', 'teknisi', 'kondisi', 'keterangan', 'Tanggal']
        params = [f"{k}" for k, v in row.items() if k not in exclude and v == "v"]
        param_text = ", ".join(params) if params else "-"
        pdf.cell(60, 7, str(row['Nama Aset'])[:40], border=1)
        pdf.cell(35, 7, str(row['teknisi']), border=1, align="C")
        pdf.cell(35, 7, str(row['kondisi']), border=1, align="C")
        pdf.cell(147, 7, param_text[:110], border=1, ln=True)
    if (210 - pdf.get_y()) < 55: pdf.add_page()
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(138, 5, "Diketahui,", 0, 0, "C")
    pdf.cell(138, 5, "Dibuat Oleh,", 0, 1, "C")
    pdf.cell(138, 5, f"{p_sel['posisi']}", 0, 0, "C")
    pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
    pdf.ln(16)
    pdf.set_font("Helvetica", "BU", 9)
    pdf.cell(138, 5, f"{p_sel['nama']}", 0, 0, "C")
    pdf.cell(138, 5, f"{t_sel['nama']}", 0, 1, "C")
    pdf.set_font("Helvetica", "", 9)
    jab_bi = p_sel['jabatan_pdf'] if p_sel['jabatan_pdf'] and p_sel['jabatan_pdf'] != 'None' else ""
    pdf.cell(138, 5, f"{jab_bi}", 0, 0, "C")
    pdf.cell(138, 5, f"{t_sel['posisi']}", 0, 1, "C")
    return bytes(pdf.output())

def render_sow_checklist(nama_unit):
    st.info(f"📋 Parameter SOW: {nama_unit}")
    ck = {}
    if "Chiller" in nama_unit:
        ck['Listrik'] = st.radio("Sistem Kelistrikan Chiller", ["Normal", "Abnormal"])
        ck['Kondensor'] = st.radio("Pembersihan Sirip Kondensor", ["Sudah", "Belum"])
        ck['Oli_Freon'] = st.radio("Oli & Freon (Sesuai Standar)", ["Ya", "Tidak"])
        ck['Arus_Ampere'] = st.text_input("Arus Kompresor & Fan (Ampere)")
        ck['Valve'] = st.radio("Kondisi Semua Valve", ["Berfungsi Baik", "Macet/Rusak"])
    elif "AC" in nama_unit:
        ck['Listrik_AC'] = st.radio("Sistem Kelistrikan", ["Normal", "Abnormal"])
        ck['Filter_Evap'] = st.radio("Filter & Evaporator (Sirip)", ["Bersih", "Kotor"])
        ck['Blower'] = st.radio("Blower Indoor/Outdoor", ["Bersih/Normal", "Berisik/Kotor"])
        ck['Drainase'] = st.radio("Saluran Drainase (Bak Air)", ["Lancar", "Tersumbat"])
    # ... (SOW lainnya tetap sama)
    else:
        ck['Catatan'] = st.text_area("Detail Pengecekan Umum")
    return ck

# --- HEADER APLIKASI ---
st.markdown("<h1 class='main-title'>🚀 SIMANTAP BI BPP</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Sistem Monitoring & Aplikasi Pemeliharaan ME - KPwBI Balikpapan</p>", unsafe_allow_html=True)

# --- LOGIKA HALAMAN ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

if st.session_state.halaman == 'Menu Utama':
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋\n\nChecklist Rutin"): ganti_hal('Rutin'); st.rerun()
        if st.button("✅\n\nUpdate Perbaikan"): ganti_hal('Update'); st.rerun()
    with col2:
        if st.button("⚠️\n\nLapor Gangguan"): ganti_hal('Gangguan'); st.rerun()
        if st.button("📊\n\nDashboard & PDF"): ganti_hal('Export'); st.rerun()

else:
    if st.button("⬅️ Kembali ke Menu Utama"):
        ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    # MODUL 1: RUTIN
    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Checklist Pemeliharaan Rutin")
        staff_data = get_staff_data()
        list_tek = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']
        sel_label = st.selectbox("Pilih Aset", options=list(options.keys()))
        asset = options[sel_label]
        with st.form("f_rutin"):
            tek = st.selectbox("Nama Teknisi", options=list_tek)
            res = render_sow_checklist(asset['nama_aset'])
            kon = st.radio("Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
            ket = st.text_area("Keterangan")
            siap_cam = st.checkbox("📸 Aktifkan Kamera")
            foto = st.camera_input("Foto Bukti") if siap_cam else None
            if st.form_submit_button("SIMPAN LAPORAN"):
                url = None
                if foto:
                    fn = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                    url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
                supabase.table("maintenance_logs").insert({"asset_id": asset['id'], "teknisi": tek, "kondisi": kon, "keterangan": ket, "foto_url": url, "checklist_data": res}).execute()
                st.success("Tersimpan!"); st.balloons()

    # MODUL 2: GANGGUAN
    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Laporan Kerusakan Mendadak")
        sel_g = st.selectbox("Aset Bermasalah", options=list(options.keys()))
        asset_g = options[sel_g]
        with st.form("f_gng"):
            pel = st.selectbox("Pelapor", options=[s['nama'] for s in get_staff_data() if s['kategori'] == 'TEKNISI'])
            mas = st.text_area("Deskripsi Masalah")
            urg = st.select_slider("Urgensi", options=["Rendah", "Sedang", "Darurat"])
            siap_g = st.checkbox("📸 Aktifkan Kamera")
            foto_g = st.camera_input("Bukti") if siap_g else None
            if st.form_submit_button("KIRIM LAPORAN"):
                url_g = None
                if foto_g:
                    fn_g = f"GNG_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_g, foto_g.getvalue())
                    url_g = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_g)
                supabase.table("gangguan_logs").insert({"asset_id": asset_g['id'], "teknisi": pel, "masalah": mas, "urgensi": urg, "status": "Open", "foto_kerusakan_url": url_g}).execute()
                st.error("Laporan Terkirim!")

    # MODUL 3: UPDATE PERBAIKAN
    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Update Penyelesaian Perbaikan")
        issues = get_open_issues()
        if not issues: st.info("Tidak ada gangguan aktif.")
        else:
            iss_opt = {f"[{i['urgensi']}] {i['assets']['nama_aset']}": i for i in issues}
            sel_i = st.selectbox("Pilih Kerusakan Selesai", list(iss_opt.keys()))
            dat_i = iss_opt[sel_i]
            with st.form("f_fix"):
                tek_p = st.selectbox("Teknisi Eksekutor", options=[s['nama'] for s in get_staff_data() if s['kategori'] == 'TEKNISI'])
                tin = st.text_area("Tindakan yang Dilakukan")
                siap_f = st.checkbox("📸 Aktifkan Kamera")
                f_a = st.camera_input("Foto Selesai") if siap_f else None
                if st.form_submit_button("UPDATE SELESAI"):
                    url_a = None
                    if f_a:
                        fn_a = f"FIX_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_a, f_a.getvalue())
                        url_a = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_a)
                    supabase.table("gangguan_logs").update({"status": "Resolved", "tindakan_perbaikan": tin, "teknisi_perbaikan": tek_p, "tgl_perbaikan": datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url": url_a}).eq("id", dat_i['id']).execute()
                    st.success("Aset Normal Kembali!")

    # MODUL 4: DASHBOARD & EXPORT
    elif st.session_state.halaman == 'Export':
        st.subheader("📊 Monitoring & Export PDF")
        logs = get_all_maintenance_logs()
        if logs:
            df = pd.DataFrame(logs)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'])
            df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Laporan", len(df))
            c2.metric("Gangguan Aktif", len(get_open_issues()))
            c3.metric("Aset", len(asset_data))
            
            d_p = st.date_input("Pilih Tanggal Laporan", datetime.date.today())
            df_f = df[df['Tanggal'] == d_p].copy()
            if not df_f.empty:
                c_df = pd.json_normalize(df_f['checklist_data'])
                df_fin = pd.concat([df_f[['Nama Aset', 'teknisi', 'kondisi', 'keterangan']].reset_index(drop=True), c_df.reset_index(drop=True)], axis=1)
                for k in ["Sudah", "Normal", "Baik", "Lancar", "Bersih", "Ya", "OK"]: df_fin = df_fin.replace(k, "v")
                st.dataframe(df_fin.fillna("-"), use_container_width=True)
                
                st.write("### Tanda Tangan")
                staff = get_staff_data()
                n_bi = st.selectbox("Pegawai BI", [s['nama'] for s in staff if s['kategori'] == 'PEGAWAI'])
                n_tk = st.selectbox("Teknisi Utama", [s['nama'] for s in staff if s['kategori'] == 'TEKNISI'])
                p_s = [s for s in staff if s['nama'] == n_bi][0]
                t_s = [s for s in staff if s['nama'] == n_tk][0]
                
                pdf = generate_pdf_simantap(df_fin.fillna("-"), d_p, p_s, t_s)
                st.download_button("📥 Download PDF", pdf, f"Laporan_{d_p}.pdf", "application/pdf")