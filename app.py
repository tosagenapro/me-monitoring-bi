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

# --- 2. CSS NEON CYBER UI ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Background Dark Digital */
    .stApp {
        background: radial-gradient(circle, #0f172a 0%, #020617 100%);
    }

    /* Header Neon */
    .main-header {
        text-align: center;
        padding: 30px;
        background: rgba(30, 58, 138, 0.1);
        border-bottom: 2px solid #38bdf8;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
        margin-bottom: 40px;
        border-radius: 0 0 20px 20px;
    }
    .main-header h1 {
        color: #f8fafc;
        font-size: 2.5rem;
        text-shadow: 0 0 12px #38bdf8;
        margin: 0;
    }
    .main-header p { color: #38bdf8; letter-spacing: 2px; font-weight: 300; }

    /* Tombol Glassmorphism */
    div.stButton > button {
        width: 100%;
        height: 190px !important;
        border-radius: 20px !important;
        background: rgba(255, 255, 255, 0.03) !important;
        color: transparent !important; /* Sembunyikan teks bawaan */
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        backdrop-filter: blur(5px);
        transition: 0.4s ease;
    }
    div.stButton > button:hover {
        background: rgba(56, 189, 248, 0.1) !important;
        border: 1px solid #38bdf8 !important;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.4) !important;
        transform: translateY(-8px);
    }

    /* Teks Menu Neon */
    .btn-text {
        font-weight: 700;
        color: #38bdf8;
        font-size: 0.95rem;
        margin-top: 15px;
        letter-spacing: 1.5px;
        text-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
    }

    /* Form & Input Styling agar terbaca di Dark Mode */
    .stSelectbox, .stTextInput, .stTextArea, .stRadio, .stDateInput {
        color: white !important;
    }
    label { color: #38bdf8 !important; font-weight: bold; }
    .stMarkdown, p { color: #cbd5e1; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI LOGIKA (DATABASE & PDF) ---
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

# --- 4. NAVIGASI ---
if 'halaman' not in st.session_state:
    st.session_state.halaman = 'Menu Utama'

def ganti_hal(nama_hal):
    st.session_state.halaman = nama_hal

# --- 5. HEADER ---
st.markdown("""
    <div class="main-header">
        <h1>⚡ SIMANTAP BI</h1>
        <p>INTEGRATED DIGITAL MAINTENANCE SYSTEM</p>
    </div>
    """, unsafe_allow_html=True)

# --- 6. LOGIKA DATA ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}
staff_all = get_staff_data()
list_tek = [s['nama'] for s in staff_all if s['kategori'] == 'TEKNISI']

# --- 7. TAMPILAN HALAMAN ---
if st.session_state.halaman == 'Menu Utama':
    st.write("##")
    _, col_pusat, _ = st.columns([0.1, 0.8, 0.1])
    
    with col_pusat:
        m1, m2 = st.columns(2)
        
        with m1:
            # Tombol 1
            if st.button(" ", key="btn_checklist"):
                ganti_hal('Rutin'); st.rerun()
            st.markdown('<div style="margin-top:-165px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/checklist.png" width="75"><div class="btn-text">CHECKLIST RUTIN</div></div><br>', unsafe_allow_html=True)

            # Tombol 2
            if st.button(" ", key="btn_update"):
                ganti_hal('Update'); st.rerun()
            st.markdown('<div style="margin-top:-165px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/refresh.png" width="75"><div class="btn-text">UPDATE PERBAIKAN</div></div><br>', unsafe_allow_html=True)

        with m2:
            # Tombol 3
            if st.button(" ", key="btn_gangguan"):
                ganti_hal('Gangguan'); st.rerun()
            st.markdown('<div style="margin-top:-165px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/error.png" width="75"><div class="btn-text">LAPOR GANGGUAN</div></div><br>', unsafe_allow_html=True)

            # Tombol 4
            if st.button(" ", key="btn_export"):
                ganti_hal('Export'); st.rerun()
            st.markdown('<div style="margin-top:-165px; text-align:center; pointer-events:none;"><img src="https://img.icons8.com/neon/96/combo-chart.png" width="75"><div class="btn-text">DASHBOARD & PDF</div></div><br>', unsafe_allow_html=True)

else:
    if st.button("⬅️ BACK TO SYSTEM", key="back"):
        ganti_hal('Menu Utama'); st.rerun()
    st.write("---")

    # --- MODUL 1: RUTIN ---
    if st.session_state.halaman == 'Rutin':
        st.subheader("📋 Form Checklist Pemeliharaan Rutin")
        sel_label = st.selectbox("Pilih Aset", options=list(options.keys()))
        asset = options[sel_label]
        with st.form("f_rutin", clear_on_submit=True):
            tek = st.selectbox("Nama Teknisi", options=list_tek)
            res = render_sow_checklist(asset['nama_aset'])
            kon = st.radio("Kesimpulan Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
            ket = st.text_area("Keterangan Tambahan")
            foto = st.camera_input("Ambil Foto Bukti")
            if st.form_submit_button("SIMPAN LAPORAN SOW"):
                url = None
                if foto:
                    fn = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn, foto.getvalue())
                    url = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn)
                payload = {"asset_id": asset['id'], "teknisi": tek, "kondisi": kon, "keterangan": ket, "foto_url": url, "checklist_data": res}
                supabase.table("maintenance_logs").insert(payload).execute()
                st.success("Data Berhasil Masuk Database!"); st.balloons()

    # --- MODUL 2: GANGGUAN ---
    elif st.session_state.halaman == 'Gangguan':
        st.subheader("⚠️ Laporan Kerusakan Mendadak")
        sel_gng = st.selectbox("Pilih Aset", options=list(options.keys()))
        aset_gng = options[sel_gng]
        with st.form("f_gangguan", clear_on_submit=True):
            pelapor = st.selectbox("Nama Pelapor", options=list_tek)
            masalah = st.text_area("Detail Kerusakan")
            urgensi = st.select_slider("Urgensi", options=["Rendah", "Sedang", "Darurat"])
            foto_gng = st.camera_input("Foto Kerusakan")
            if st.form_submit_button("KIRIM LAPORAN DARURAT"):
                url_g = None
                if foto_gng:
                    fn_g = f"GNG_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_g, foto_gng.getvalue())
                    url_g = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_g)
                payload_g = {"asset_id": aset_gng['id'], "teknisi": pelapor, "masalah": masalah, "urgensi": urgensi, "status": "Open", "foto_kerusakan_url": url_g}
                supabase.table("gangguan_logs").insert(payload_g).execute()
                st.error("Laporan Dikirim!")

    # --- MODUL 3: UPDATE ---
    elif st.session_state.halaman == 'Update':
        st.subheader("✅ Form Penyelesaian Perbaikan")
        issues = get_open_issues()
        if not issues:
            st.info("Tidak ada gangguan aktif.")
        else:
            issue_options = {f"[{i['urgensi']}] {i['assets']['nama_aset']}": i for i in issues}
            sel_i = st.selectbox("Pilih Gangguan", options=list(issue_options.keys()))
            dat_i = issue_options[sel_i]
            with st.form("f_perbaikan"):
                t_per = st.selectbox("Teknisi Pelaksana", options=list_tek)
                tin = st.text_area("Tindakan")
                f_after = st.camera_input("Foto Selesai")
                if st.form_submit_button("UPDATE STATUS: SELESAI"):
                    url_a = None
                    if f_after:
                        fn_a = f"FIX_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("FOTO_MAINTENANCE").upload(fn_a, f_after.getvalue())
                        url_a = supabase.storage.from_("FOTO_MAINTENANCE").get_public_url(fn_a)
                    supabase.table("gangguan_logs").update({"status": "Resolved", "tindakan_perbaikan": tin, "teknisi_perbaikan": t_per, "tgl_perbaikan": datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url": url_a}).eq("id", dat_i['id']).execute()
                    st.success("Aset Normal Kembali!"); st.balloons()

    # --- MODUL 4: EXPORT ---
    elif st.session_state.halaman == 'Export':
        st.subheader("📊 Dashboard & Penarikan PDF")
        raw_logs = get_all_maintenance_logs()
        if raw_logs:
            df = pd.DataFrame(raw_logs)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Laporan Rutin", len(df))
            c2.metric("Gangguan Open", len(get_open_issues()))
            c3.metric("Total Aset", len(asset_data))

            d_pilih = st.date_input("Pilih Tanggal Laporan", datetime.date.today())
            df_filtered = df[df['Tanggal'] == d_pilih].copy()
            if not df_filtered.empty:
                ck_df = pd.json_normalize(df_filtered['checklist_data'])
                df_final = pd.concat([df_filtered[['Nama Aset', 'teknisi', 'kondisi', 'keterangan']].reset_index(drop=True), ck_df.reset_index(drop=True)], axis=1)
                
                # Standarisasi Nilai
                ok_vals = ["Sudah", "Normal", "Baik", "Lancar", "Bersih", "Ya", "Berfungsi Baik", "OK"]
                for k in ok_vals: df_final = df_final.replace(k, "v")
                df_final = df_final.fillna("-")
                
                st.dataframe(df_final, use_container_width=True)
                
                peg_bi = [s for s in staff_all if s['kategori'] == 'PEGAWAI']
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    n_bi = st.selectbox("Mengetahui (BI):", [s['nama'] for s in peg_bi])
                    p_sel = [s for s in peg_bi if s['nama'] == n_bi][0]
                with col_s2:
                    n_tk = st.selectbox("Dibuat Oleh (ME):", list_tek)
                    t_sel = [s for s in staff_all if s['nama'] == n_tk][0]

                if st.download_button("📥 DOWNLOAD PDF", generate_pdf_simantap(df_final, d_pilih, p_sel, t_sel), f"LAP_{d_pilih}.pdf", "application/pdf"):
                    st.success("PDF Berhasil Dibuat")
            else:
                st.warning("Data kosong pada tanggal ini.")