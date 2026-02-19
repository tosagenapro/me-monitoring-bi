import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF

# --- CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP BI BPP", layout="wide")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNGSI AMBIL DATA DARI DATABASE ---
def get_assets():
    return supabase.table("assets").select("id, nama_aset, kategori, kode_qr").order("nama_aset").execute().data

def get_open_issues():
    return supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute().data

def get_all_maintenance_logs():
    return supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute().data

def get_staff_data():
    return supabase.table("staff_me").select("*").execute().data

# --- FUNGSI GENERATOR PDF (FORMAT RESMI BI - LANDSCAPE) ---
def generate_pdf_simantap(df, tgl, p_sel, t_sel):
    # p_sel & t_sel adalah dictionary data lengkap dari database staff_me
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # Header Judul
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "CHECKLIST HARIAN TEKNISI ME - KPwBI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Tanggal Pekerjaan: {tgl}", ln=True, align="C")
    pdf.ln(3)
    pdf.line(10, 26, 287, 26) 
    pdf.ln(5)

    # Table Header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(60, 8, "Nama Aset", border=1, fill=True, align="C")
    pdf.cell(35, 8, "Teknisi", border=1, fill=True, align="C")
    pdf.cell(35, 8, "Kondisi", border=1, fill=True, align="C")
    pdf.cell(147, 8, "Detail Parameter SOW", border=1, fill=True, align="C", ln=True)

    # Table Body
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        exclude = ['Nama Aset', 'teknisi', 'kondisi', 'keterangan', 'Tanggal']
        params = [f"{k}" for k, v in row.items() if k not in exclude and v == "v"]
        param_text = ", ".join(params) if params else "-"
        
        pdf.cell(60, 7, str(row['Nama Aset'])[:40], border=1)
        pdf.cell(35, 7, str(row['teknisi']), border=1, align="C")
        pdf.cell(35, 7, str(row['kondisi']), border=1, align="C")
        pdf.cell(147, 7, param_text[:110], border=1, ln=True)
        
    # --- FORMAT TANDA TANGAN DINAMIS ---
    pdf.set_y(-55) 
    pdf.set_font("Helvetica", "B", 9)
    
    # Baris 1: Judul
    pdf.cell(138, 5, "Diketahui,", 0, 0, "C")
    pdf.cell(138, 5, "Dibuat Oleh,", 0, 1, "C")
    
    # Baris 2: Posisi Pegawai & Nama CV Permanen
    pdf.cell(138, 5, f"{p_sel['posisi']}", 0, 0, "C")
    pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
    
    pdf.ln(16) # Ruang Tanda Tangan
    
    # Baris 3: Nama (Keduanya Garis Bawah / Underline)
    pdf.set_font("Helvetica", "BU", 9)
    pdf.cell(138, 5, f"{p_sel['nama']}", 0, 0, "C")
    pdf.cell(138, 5, f"{t_sel['nama']}", 0, 1, "C")
    
    # Baris 4: Jabatan_pdf Pegawai & Posisi Teknisi
    pdf.set_font("Helvetica", "", 9)
    jab_bi = p_sel['jabatan_pdf'] if p_sel['jabatan_pdf'] else ""
    pdf.cell(138, 5, f"{jab_bi}", 0, 0, "C")
    pdf.cell(138, 5, f"{t_sel['posisi']}", 0, 1, "C")

    return bytes(pdf.output())

# --- FUNGSI CHECKLIST SOW ---
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

# --- MAIN APP ---
st.title("🚀 SIMANTAP BI BPP")
st.markdown("### Sistem Informasi Monitoring dan Aplikasi Pemeliharaan ME")
st.markdown("##### KPwBI Balikpapan")
st.write("---")

asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

tab1, tab2, tab3, tab4 = st.tabs(["📋 Checklist Rutin", "⚠️ Lapor Gangguan", "✅ Update Perbaikan", "📊 Dashboard & Export"])

with tab1:
    staff_data = get_staff_data()
    # List teknisi untuk dropdown input agar tidak typo
    list_tek_input = [s['nama'] for s in staff_data if s['kategori'] == 'TEKNISI']
    
    selected_label = st.selectbox("Pilih Aset (Rutin)", options=list(options.keys()))
    selected_asset = options[selected_label]
    
    with st.form("form_rutin_final", clear_on_submit=True):
        nama_teknisi = st.selectbox("Nama Teknisi", options=list_tek_input)
        results = render_sow_checklist(selected_asset['nama_aset'])
        st.write("---")
        kondisi_final = st.radio("Kesimpulan Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
        tindakan = st.text_area("Keterangan Tambahan")
        foto = st.camera_input("Ambil Foto Bukti")
        
        if st.form_submit_button("Simpan Laporan SOW"):
            url_f = None
            if foto:
                fn = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                supabase.storage.from_("foto_maintenance").upload(fn, foto.getvalue())
                url_f = supabase.storage.from_("foto_maintenance").get_public_url(fn)
            
            payload = {
                "asset_id": selected_asset['id'], 
                "teknisi": nama_teknisi, 
                "kondisi": kondisi_final, 
                "keterangan": tindakan, 
                "foto_url": url_f, 
                "checklist_data": results
            }
            supabase.table("maintenance_logs").insert(payload).execute()
            st.success("Laporan Berhasil Disimpan!")
            st.balloons()

with tab2:
    st.warning("Hanya untuk laporan kerusakan mendadak!")
    sel_gng = st.selectbox("Pilih Aset Bermasalah", options=list(options.keys()), key="sel_g2")
    aset_gng = options[sel_gng]
    with st.form("form_gangguan_final", clear_on_submit=True):
        # Gunakan dropdown teknisi juga di sini
        pelapor = st.selectbox("Nama Pelapor/Teknisi", options=list_tek_input)
        masalah = st.text_area("Deskripsi Kerusakan")
        urgensi = st.select_slider("Tingkat Urgensi", options=["Rendah", "Sedang", "Darurat"])
        foto_gng = st.camera_input("Foto Bukti Kerusakan")
        if st.form_submit_button("KIRIM LAPORAN DARURAT"):
            url_g = None
            if foto_gng:
                fn_g = f"GNG_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                supabase.storage.from_("foto_maintenance").upload(fn_g, foto_gng.getvalue())
                url_g = supabase.storage.from_("foto_maintenance").get_public_url(fn_g)
            
            payload_g = {
                "asset_id": aset_gng['id'], 
                "teknisi": pelapor, 
                "masalah": masalah, 
                "urgensi": urgensi, 
                "status": "Open", 
                "foto_kerusakan_url": url_g
            }
            supabase.table("gangguan_logs").insert(payload_g).execute()
            st.error("Laporan Gangguan telah dikirim!")

with tab3:
    st.subheader("Penyelesaian Laporan Kerusakan")
    issues = get_open_issues()
    if not issues:
        st.info("Semua aset dalam kondisi aman.")
    else:
        issue_options = {f"[{i['urgensi']}] {i['assets']['nama_aset']} - {i['masalah'][:30]}...": i for i in issues}
        sel_issue_label = st.selectbox("Pilih Laporan Selesai", options=list(issue_options.keys()))
        issue_data = issue_options[sel_issue_label]
        with st.form("form_perbaikan_final"):
            t_perbaikan = st.selectbox("Nama Teknisi Perbaikan", options=list_tek_input)
            tindakan_p = st.text_area("Tindakan/Kronologi Perbaikan")
            f_after = st.camera_input("Foto After")
            if st.form_submit_button("Update Status: SELESAI"):
                url_a = None
                if f_after:
                    fn_a = f"FIX_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("foto_maintenance").upload(fn_a, f_after.getvalue())
                    url_a = supabase.storage.from_("foto_maintenance").get_public_url(fn_a)
                
                supabase.table("gangguan_logs").update({
                    "status": "Resolved", 
                    "tindakan_perbaikan": tindakan_p, 
                    "teknisi_perbaikan": t_perbaikan, 
                    "tgl_perbaikan": datetime.datetime.now().isoformat(), 
                    "foto_setelah_perbaikan_url": url_a
                }).eq("id", issue_data['id']).execute()
                st.success("Status Aset kembali Normal!")

with tab4:
    st.subheader("📊 Dashboard & Penarikan Laporan")
    raw_logs = get_all_maintenance_logs()
    if raw_logs:
        df = pd.DataFrame(raw_logs)
        df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
        df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Laporan", len(df))
        c2.metric("Gangguan Aktif", len(get_open_issues()), delta_color="inverse")
        c3.metric("Aset Terdaftar", len(asset_data))
        
        st.write("---")
        st.write("### 🔍 Tarik Laporan Harian")
        d_pilih = st.date_input("Pilih Tanggal Laporan", datetime.date.today())
        df_filtered = df[df['Tanggal'] == d_pilih].copy()

        if not df_filtered.empty:
            # Formatting data table
            checklist_df = pd.json_normalize(df_filtered['checklist_data'])
            df_final = pd.concat([df_filtered[['Nama Aset', 'teknisi', 'kondisi', 'keterangan']].reset_index(drop=True), checklist_df.reset_index(drop=True)], axis=1)
            
            kata_kunci = ["Sudah", "Normal", "Baik", "Lancar", "Bersih", "Ya", "Berfungsi Baik", "Lengkap/Baik", "OK"]
            for kata in kata_kunci:
                df_final = df_final.replace(kata, "v")
            df_final = df_final.fillna("-")

            st.dataframe(df_final, use_container_width=True)
            
            # --- PENGATURAN TANDA TANGAN (DATABASE STAFF) ---
            st.write("### ✍️ Konfirmasi Tanda Tangan Laporan")
            staff_all = get_staff_data()
            pegawai_bi = [s for s in staff_all if s['kategori'] == 'PEGAWAI']
            teknisi_me = [s for s in staff_all if s['kategori'] == 'TEKNISI']
            
            col_sign1, col_sign2 = st.columns(2)
            with col_sign1:
                n_bi = st.selectbox("Pilih Pegawai BI (Diketahui):", [s['nama'] for s in pegawai_bi])
                p_sel = [s for s in pegawai_bi if s['nama'] == n_bi][0]
            with col_sign2:
                n_tek = st.selectbox("Pilih Teknisi (Dibuat):", [s['nama'] for s in teknisi_me])
                t_sel = [s for s in teknisi_me if s['nama'] == n_tek][0]

            # Generate PDF
            pdf_data = generate_pdf_simantap(df_final, d_pilih, p_sel, t_sel)
            
            st.download_button(
                label="📥 Download Laporan PDF (Landscape Resmi)",
                data=pdf_data,
                file_name=f"Laporan_SIMANTAP_{d_pilih}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning(f"Tidak ada data pada tanggal {d_pilih}")