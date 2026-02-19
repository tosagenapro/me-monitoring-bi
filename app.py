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

# --- 2. CUSTOM CSS (TAMPILAN MODERN DENGAN IKON PNG) ---
st.markdown("""
    <style>
    /* Menghilangkan elemen default Streamlit */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Background Utama */
    .stApp {
        background-color: #f0f2f6; /* Light gray background */
    }

    /* Header Biru Gelap Mengkilap */
    .main-header {
        text-align: center;
        padding: 25px;
        background: linear-gradient(135deg, #0A1931 0%, #1A4080 100%); /* Dark Blue Gradient */
        color: white;
        border-radius: 0 0 40px 40px;
        margin-bottom: 40px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: 1.5px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .main-header p {
        margin: 5px 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 300;
    }

    /* Styling Tombol Menu Utama (Card Style) */
    div.stButton > button {
        width: 100%;
        height: 180px !important; /* Diperbesar agar mirip mockup */
        border-radius: 25px !important;
        border: none !important;
        background-color: white !important;
        color: #0A1931 !important; /* Warna teks gelap */
        font-size: 16px !important;
        font-weight: bold !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease-in-out !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 15px;
    }

    div.stButton > button:hover {
        transform: translateY(-8px) !important;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2) !important;
        border: 2px solid #1A4080 !important; /* Border biru saat hover */
        color: #1A4080 !important;
    }

    /* Untuk teks di dalam tombol */
    .btn-text {
        display: block;
        margin-top: 10px;
        font-size: 1.1rem;
        line-height: 1.3;
    }
    .st-emotion-cache-1pxpz75 {
        gap: 20px; /* Jarak antar kolom tombol */
    }
    .st-emotion-cache-1q1n031 {
        padding-top: 20px; /* Sedikit padding atas untuk konten */
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI-FUNGSI LOGIKA (Sama seperti sebelumnya) ---
@st.cache_data(ttl=60)
def get_assets():
    return supabase.table("assets").select("id, nama_aset, kategori, kode_qr").order("nama_aset").execute().data

@st.cache_data(ttl=60)
def get_open_issues():
    return supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute().data

@st.cache_data(ttl=60)
def get_all_maintenance_logs():
    return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

@st.cache_data(ttl=60)
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
    if "Chiller" in nama_unit:
        ck['Listrik'] = st.radio("Sistem Kelistrikan Chiller", ["Normal", "Abnormal"])
        ck['Kondensor'] = st.radio("Pembersihan Sirip Kondensor", ["Sudah", "Belum"])
        ck['Oli_Freon'] = st.radio("Oli & Freon (Sesuai Standar)", ["Ya", "Tidak"])
        ck['Arus_Ampere'] = st.text_input("Arus Kompresor & Fan (Ampere)")
        ck['Valve'] = st.radio("Kondisi Semua Valve", ["Berfungsi Baik", "Macet/Rusak"])
    elif "Cooling Tower" in nama_unit:
        ck['Belt_Fan'] = st.radio("Tension Belt & Motor Fan", ["OK", "Perlu Setel"])
        ck['Lumpur'] = st.radio("Lower Basin (Lumpur/Kotoran)", ["Bersih", "Kotor"])
    elif "AHU" in nama_unit:
        ck['Cuci_Filter'] = st.radio("Pencucian Filter Udara", ["Sudah", "Belum"])
        ck['Thermostat'] = st.radio("Thermostat ON/OFF", ["Normal", "Rusak"])
        ck['Mekanis'] = st.radio("V-Belt, Bearing, Mounting", ["Kondisi Baik", "Perlu Perbaikan"])
        ck['Temp_Air'] = st.text_input("Temperatur Air In/Out (°C)")
    elif "AC" in nama_unit:
        ck['Listrik_AC'] = st.radio("Sistem Kelistrikan", ["Normal", "Abnormal"])
        ck['Filter_Evap'] = st.radio("Filter & Evaporator (Sirip)", ["Bersih", "Kotor"])
        ck['Blower'] = st.radio("Blower Indoor/Outdoor", ["Bersih/Normal", "Berisik/Kotor"])
        ck['Drainase'] = st.radio("Saluran Drainase (Bak Air)", ["Lancar", "Tersumbat"])
    elif "Genset" in nama_unit:
        ck['Accu'] = st.radio("Kondisi Accu & Air Accu", ["Baik", "Perlu Maintenance"])
        ck['Radiator'] = st.radio("Kondisi Radiator", ["Bersih/Cukup", "Kotor/Kurang"])
        ck['Filter_Solar_Oli'] = st.radio("Kondisi Filter Solar/Oli", ["Baik", "Perlu Ganti"])
    elif "UPS" in nama_unit:
        ck['Display'] = st.radio("Pemeriksaan Display", ["Normal", "Error/Alarm"])
        ck['Input_Volt'] = st.text_input("Input Listrik (Volt)")
        ck['Batt_Volt'] = st.text_input("Tegangan Baterai (VDC)")
        ck['Load'] = st.text_input("Beban Daya Output (%)")
    elif "Panel" in nama_unit or "Kubikel" in nama_unit:
        ck['Komponen'] = st.radio("Kondisi MCB, Busbar, Lampu Indikator", ["Lengkap/Baik", "Bermasalah"])
        ck['Kebersihan'] = st.radio("Kebersihan Dalam/Luar Panel", ["Bersih", "Kotor"])
    else:
        ck['Catatan'] = st.text_area("Detail Pengecekan Umum")
    return ck

# --- 4. NAVIGASI SESSION STATE ---
if 'halaman' not in st.session_state:
    st.session_state.halaman = 'Menu Utama'

def ganti_hal(nama_hal):
    st.session_state.halaman = nama_hal

# --- 5. HEADER APLIKASI ---
st.markdown("""
    <div class="main-header">
        <h1>SIMANTAP BI BPP</h1>
        <p>Sistem Informasi Monitoring dan Aplikasi Pemeliharaan ME</p>
    </div>
    """, unsafe_allow_html=True)

# --- 6. LOGIKA HALAMAN ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}
staff_all = get_staff_data()
list_tek = [s['nama'] for s in staff_all if s['kategori'] == 'TEKNISI']

if st.session_state.halaman == 'Menu Utama':
    st.write("##") # Spasi untuk estetika
    _, col_menu_tengah, _ = st.columns([0.1, 0.8, 0.1]) # Kolom untuk memusatkan menu
    
    with col_menu_tengah:
        m1, m2 = st.columns(2)
        
        # --- KOLOM 1: CHECKLIST & UPDATE ---
        with m1:
            # Tombol 1: Checklist Rutin
            if st.button(" ", key="btn_checklist"):
                ganti_hal('Rutin'); st.rerun()
            st.markdown(f"""
                <div style="margin-top: -145px; text-align: center; pointer-events: none;">
                    <img src="https://cdn-icons-png.flaticon.com/512/9482/9482614.png" width="80">
                    <div class="btn-text">CHECKLIST RUTIN</div>
                </div><br>""", unsafe_allow_html=True)

            # Tombol 2: Update Perbaikan
            if st.button(" ", key="btn_update_perbaikan"):
                ganti_hal('Update'); st.rerun()
            st.markdown(f"""
                <div style="margin-top: -145px; text-align: center; pointer-events: none;">
                    <img src="https://cdn-icons-png.flaticon.com/512/1162/1162283.png" width="80">
                    <div class="btn-text">UPDATE PERBAIKAN</div>
                </div><br>""", unsafe_allow_html=True)

        # --- KOLOM 2: GANGGUAN & DASHBOARD ---
        with m2:
            # Tombol 3: Lapor Gangguan
            if st.button(" ", key="btn_lapor_gangguan"):
                ganti_hal('Gangguan'); st.rerun()
            st.markdown(f"""
                <div style="margin-top: -145px; text-align: center; pointer-events: none;">
                    <img src="https://cdn-icons-png.flaticon.com/512/595/595067.png" width="80">
                    <div class="btn-text">LAPOR GANGGUAN</div>
                </div><br>""", unsafe_allow_html=True)

            # Tombol 4: Dashboard & Export PDF
            if st.button(" ", key="btn_dashboard_pdf"):
                ganti_hal('Export'); st.rerun()
            st.markdown(f"""
                <div style="margin-top: -145px; text-align: center; pointer-events: none;">
                    <img src="https://cdn-icons-png.flaticon.com/512/1162/1162251.png" width="80">
                    <div class="btn-text">DASHBOARD & PDF</div>
                </div><br>""", unsafe_allow_html=True)

else:
    # Tombol Kembali
    if st.button("⬅️ Kembali ke Menu Utama", key="back_to_menu"):
        ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    # --- MODUL 1: CHECKLIST RUTIN ---
    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Form Checklist Pemeliharaan Rutin")
        sel_label = st.selectbox("Pilih Aset", options=list(options.keys()))
        asset = options[sel_label]
        with st.form("f_rutin", clear_on_submit=True):
            tek = st.selectbox("Nama Teknisi", options=list_tek)
            res = render_sow_checklist(asset['nama_aset'])
            kon = st.radio("Kesimpulan Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1) # Default ke 'Baik'
            ket = st.text_area("Keterangan Tambahan (jika ada)")
            siap_cam = st.checkbox("📸 Aktifkan Kamera untuk Bukti Dokumentasi")
            foto = st.camera_input("Ambil Foto (Opsional)") if siap_cam else None
            if st.form_submit_button("SIMPAN LAPORAN SOW"):
                url = None
                if foto:
                    fn = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                    url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
                payload = {"asset_id": asset['id'], "teknisi": tek, "kondisi": kon, "keterangan": ket, "foto_url": url, "checklist_data": res}
                supabase.table("maintenance_logs").insert(payload).execute()
                st.success("Laporan Rutin Berhasil Disimpan!"); st.balloons()

    # --- MODUL 2: LAPOR GANGGUAN ---
    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Laporan Kerusakan Mendadak")
        st.warning("Gunakan modul ini hanya untuk melaporkan gangguan/kerusakan yang sifatnya mendadak dan membutuhkan penanganan segera.")
        sel_gng = st.selectbox("Pilih Aset yang Bermasalah", options=list(options.keys()), key="sel_g2")
        aset_gng = options[sel_gng]
        with st.form("form_gangguan_final", clear_on_submit=True):
            pelapor = st.selectbox("Nama Pelapor/Teknisi", options=list_tek)
            masalah = st.text_area("Deskripsi Detail Kerusakan")
            urgensi = st.select_slider("Tingkat Urgensi", options=["Rendah", "Sedang", "Darurat"], value="Sedang")
            siap_kamera_g = st.checkbox("📸 Aktifkan Kamera untuk Bukti Kerusakan")
            foto_gng = st.camera_input("Ambil Foto Kerusakan") if siap_kamera_g else None
            
            if st.form_submit_button("KIRIM LAPORAN DARURAT"):
                url_g = None
                if foto_gng:
                    fn_g = f"GNG_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_g, foto_gng.getvalue())
                    url_g = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_g)
                
                payload_g = {"asset_id": aset_gng['id'], "teknisi": pelapor, "masalah": masalah, "urgensi": urgensi, "status": "Open", "foto_kerusakan_url": url_g}
                supabase.table("gangguan_logs").insert(payload_g).execute()
                st.error("Laporan Gangguan telah berhasil dikirim!")

    # --- MODUL 3: UPDATE PERBAIKAN ---
    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Form Penyelesaian Laporan Kerusakan")
        issues = get_open_issues()
        if not issues:
            st.info("Semua aset dalam kondisi normal, tidak ada laporan gangguan yang perlu ditindaklanjuti.")
        else:
            issue_options = {f"[{i['urgensi']}] {i['assets']['nama_aset']} - {i['masalah'][:40]}...": i for i in issues}
            sel_issue_label = st.selectbox("Pilih Laporan Gangguan yang Sudah Selesai Diperbaiki", options=list(issue_options.keys()))
            issue_data = issue_options[sel_issue_label]
            
            with st.form("form_perbaikan_final", clear_on_submit=True):
                st.info(f"Detail Laporan: **{issue_data['assets']['nama_aset']}** - {issue_data['masalah']}")
                st.write(f"Pelapor: {issue_data['teknisi']} (Urgensi: {issue_data['urgensi']})")

                t_perbaikan = st.selectbox("Nama Teknisi Pelaksana Perbaikan", options=list_tek)
                tindakan_p = st.text_area("Tindakan yang Telah Dilakukan (Kronologi Perbaikan)")
                
                siap_kamera_f = st.checkbox("📸 Aktifkan Kamera untuk Bukti Setelah Perbaikan")
                f_after = st.camera_input("Ambil Foto Setelah Perbaikan") if siap_kamera_f else None
                
                if st.form_submit_button("UPDATE STATUS: SELESAI"):
                    url_a = None
                    if f_after:
                        fn_a = f"FIX_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_a, f_after.getvalue())
                        url_a = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_a)
                    
                    supabase.table("gangguan_logs").update({
                        "status": "Resolved", 
                        "tindakan_perbaikan": tindakan_p, 
                        "teknisi_perbaikan": t_perbaikan, 
                        "tgl_perbaikan": datetime.datetime.now().isoformat(), 
                        "foto_setelah_perbaikan_url": url_a
                    }).eq("id", issue_data['id']).execute()
                    st.success("Status Aset berhasil diperbarui menjadi NORMAL!"); st.balloons()

    # --- MODUL 4: DASHBOARD & EXPORT PDF ---
    elif st.session_state.halaman == 'Export':
        st.subheader("📊 Dashboard Monitoring & Penarikan Laporan Harian")
        raw_logs = get_all_maintenance_logs()
        
        if raw_logs:
            df = pd.DataFrame(raw_logs)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
            
            # KPI Metrics
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            col_kpi1.metric("Total Laporan Rutin", len(df))
            col_kpi2.metric("Gangguan Aktif", len(get_open_issues()), delta_color="inverse")
            col_kpi3.metric("Total Aset Terdaftar", len(asset_data))
            
            st.write("---")
            st.write("### 🔍 Filter dan Tarik Laporan Harian")
            d_pilih = st.date_input("Pilih Tanggal Laporan yang Akan Ditarik", datetime.date.today())
            df_filtered = df[df['Tanggal'] == d_pilih].copy()

            if not df_filtered.empty:
                # Normalisasi data checklist SOW
                checklist_df = pd.json_normalize(df_filtered['checklist_data'])
                df_final = pd.concat([df_filtered[['Nama Aset', 'teknisi', 'kondisi', 'keterangan']].reset_index(drop=True), checklist_df.reset_index(drop=True)], axis=1)
                
                # Mengganti nilai parameter SOW menjadi 'v' jika kondisi sesuai
                kata_kunci_ok = ["Sudah", "Normal", "Baik", "Lancar", "Bersih", "Ya", "Berfungsi Baik", "Lengkap/Baik", "OK"]
                for kata in kata_kunci_ok:
                    df_final = df_final.replace(kata, "v")
                df_final = df_final.fillna("-") # Mengisi nilai kosong dengan '-'
                
                st.dataframe(df_final, use_container_width=True)
                
                st.write("### ✍️ Konfirmasi Tanda Tangan untuk Laporan PDF")
                pegawai_bi = [s for s in staff_all if s['kategori'] == 'PEGAWAI']
                teknisi_me = [s for s in staff_all if s['kategori'] == 'TEKNISI']
                
                col_sign1, col_sign2 = st.columns(2)
                with col_sign1:
                    n_bi = st.selectbox("Pilih Pegawai BI (Mengetahui):", [s['nama'] for s in pegawai_bi])
                    p_sel = [s for s in pegawai_bi if s['nama'] == n_bi][0]
                with col_sign2:
                    n_tek = st.selectbox("Pilih Teknisi Utama (Dibuat Oleh):", [s['nama'] for s in teknisi_me])
                    t_sel = [s for s in teknisi_me if s['nama'] == n_tek][0]

                pdf_data = generate_pdf_simantap(df_final, d_pilih, p_sel, t_sel)
                st.download_button(
                    label="📥 Download Laporan Harian (PDF Landscape)",
                    data=pdf_data,
                    file_name=f"Laporan_SIMANTAP_Harian_{d_pilih}.pdf",
                    mime="application/pdf",
                    key="dl_pdf"
                )
            else:
                st.warning(f"Tidak ada data laporan rutin pada tanggal **{d_pilih.strftime('%d %B %Y')}**.")
        else:
            st.info("Belum ada data laporan pemeliharaan rutin di database.")