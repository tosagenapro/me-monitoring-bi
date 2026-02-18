import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# --- CONFIG & KONEKSI ---
st.set_page_config(page_title="ME Monitoring BI", layout="wide")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

st.title("🏢 Monitoring ME - BI Balikpapan")

# --- FUNGSI AMBIL DATA ---
def get_assets():
    query = supabase.table("assets").select("id, nama_aset, kategori, kode_qr").order("nama_aset").execute()
    return query.data

def get_open_issues():
    query = supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute()
    return query.data

def get_all_maintenance_logs():
    # Mengambil semua data untuk keperluan dashboard/export
    query = supabase.table("maintenance_logs").select("*, assets(nama_aset, kode_qr)").order("created_at", desc=True).execute()
    return query.data

# --- FUNGSI CHECKLIST SOW LENGKAP (Module 1) ---
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

# --- PREPARASI DATA ASET ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

# --- SISTEM TAB ---
tab1, tab2, tab3, tab4 = st.tabs(["📋 Checklist Rutin", "⚠️ Lapor Gangguan", "✅ Update Perbaikan", "📊 Dashboard & Export"])

# ==========================================
# TAB 1: MAINTENANCE RUTIN (SOW)
# ==========================================
with tab1:
    selected_label = st.selectbox("Pilih Aset (Rutin)", options=list(options.keys()), key="sel_r1")
    selected_asset = options[selected_label]
    
    with st.form("form_rutin_final", clear_on_submit=True):
        nama_teknisi = st.text_input("Nama Teknisi")
        results = render_sow_checklist(selected_asset['nama_aset'])
        
        st.write("---")
        kondisi_final = st.radio("Kesimpulan Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
        tindakan = st.text_area("Keterangan Tambahan")
        foto = st.camera_input("Ambil Foto Bukti", key="cam_r1")
        
        if st.form_submit_button("Simpan Laporan SOW"):
            if nama_teknisi:
                url_f = None
                if foto:
                    fn = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("foto_maintenance").upload(fn, foto.getvalue())
                    url_f = supabase.storage.from_("foto_maintenance").get_public_url(fn)
                
                payload = {
                    "asset_id": selected_asset['id'], "teknisi": nama_teknisi,
                    "kondisi": kondisi_final, "keterangan": tindakan,
                    "foto_url": url_f, "checklist_data": results
                }
                supabase.table("maintenance_logs").insert(payload).execute()
                st.success(f"Laporan {selected_label} Berhasil Disimpan!")
                st.balloons()
            else:
                st.error("Nama Teknisi wajib diisi!")

# ==========================================
# TAB 2: LAPOR GANGGUAN
# ==========================================
with tab2:
    st.warning("Hanya untuk laporan kerusakan mendadak!")
    sel_gng = st.selectbox("Pilih Aset Bermasalah", options=list(options.keys()), key="sel_g2")
    aset_gng = options[sel_gng]
    
    with st.form("form_gangguan_final", clear_on_submit=True):
        pelapor = st.text_input("Nama Pelapor/Teknisi")
        masalah = st.text_area("Deskripsi Kerusakan")
        urgensi = st.select_slider("Tingkat Urgensi", options=["Rendah", "Sedang", "Darurat"])
        foto_gng = st.camera_input("Foto Bukti Kerusakan", key="cam_g2")
        
        if st.form_submit_button("KIRIM LAPORAN DARURAT"):
            if pelapor and masalah:
                url_g = None
                if foto_gng:
                    fn_g = f"GNG_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("foto_maintenance").upload(fn_g, foto_gng.getvalue())
                    url_g = supabase.storage.from_("foto_maintenance").get_public_url(fn_g)
                
                payload_g = {
                    "asset_id": aset_gng['id'], "teknisi": pelapor,
                    "masalah": masalah, "urgensi": urgensi,
                    "status": "Open", "foto_kerusakan_url": url_g
                }
                supabase.table("gangguan_logs").insert(payload_g).execute()
                st.error("Laporan Gangguan telah dikirim ke Database!")
            else:
                st.warning("Nama dan Detail Masalah wajib diisi!")

# ==========================================
# TAB 3: UPDATE PERBAIKAN
# ==========================================
with tab3:
    st.subheader("Penyelesaian Laporan Kerusakan")
    issues = get_open_issues()
    if not issues:
        st.info("Alhamdulillah, semua aset dalam kondisi aman.")
    else:
        issue_options = {f"[{i['urgensi']}] {i['assets']['nama_aset']} - {i['masalah'][:30]}...": i for i in issues}
        sel_issue_label = st.selectbox("Pilih Laporan yang sudah Selesai diperbaiki", options=list(issue_options.keys()))
        issue_data = issue_options[sel_issue_label]
        
        with st.form("form_perbaikan_final"):
            t_perbaikan = st.text_input("Nama Teknisi yang Memperbaiki")
            tindakan_p = st.text_area("Tindakan/Kronologi Perbaikan")
            f_after = st.camera_input("Foto Hasil Akhir (After)", key="cam_p3")
            
            if st.form_submit_button("Update Status: SELESAI (Resolved)"):
                if t_perbaikan and tindakan_p:
                    url_a = None
                    if f_after:
                        fn_a = f"FIX_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        supabase.storage.from_("foto_maintenance").upload(fn_a, f_after.getvalue())
                        url_a = supabase.storage.from_("foto_maintenance").get_public_url(fn_a)
                    
                    supabase.table("gangguan_logs").update({
                        "status": "Resolved", "tindakan_perbaikan": tindakan_p,
                        "teknisi_perbaikan": t_perbaikan, "tgl_perbaikan": datetime.datetime.now().isoformat(),
                        "foto_setelah_perbaikan_url": url_after
                    }).eq("id", issue_data['id']).execute()
                    st.success("Data kronologi tersimpan. Status Aset kembali Normal!")
                    st.balloons()
                else:
                    st.warning("Mohon isi nama teknisi dan tindakan.")

# ==========================================
# TAB 4: DASHBOARD & EXPORT (VERSI RAPI)
# ==========================================
with tab4:
    st.subheader("📊 Monitoring & Download Laporan")
    
    raw_logs = get_all_maintenance_logs()
    
    if raw_logs:
        df = pd.DataFrame(raw_logs)
        df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
        df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
        
        st.write("### 🔍 Filter Data")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            d_mulai = st.date_input("Mulai Tanggal", datetime.date.today() - datetime.timedelta(days=7), key="filter_start")
        with col_f2:
            d_selesai = st.date_input("Sampai Tanggal", datetime.date.today(), key="filter_end")
            
        list_aset = sorted(df['Nama Aset'].unique())
        pilih_aset = st.multiselect("Pilih Unit Aset (Kosongkan untuk Semua)", list_aset, key="filter_aset")
        
        # Logika Filter
        mask = (df['Tanggal'] >= d_mulai) & (df['Tanggal'] <= d_selesai)
        if pilih_aset:
            mask = mask & (df['Nama Aset'].isin(pilih_aset))
        
        df_filtered = df.loc[mask].copy()
        
        if not df_filtered.empty:
            # --- PROSES MERAPIKAN DATA (DARI SINI KODE BARUNYA) ---
            df_export = df_filtered.copy()
            
            # Pecah kolom checklist_data yang tadinya satu kolom menjadi banyak kolom
            checklist_df = pd.json_normalize(df_export['checklist_data'])
            
            # Gabungkan data identitas dengan data hasil checklist
            df_final_export = pd.concat([
                df_export[['Tanggal', 'Nama Aset', 'teknisi', 'kondisi', 'keterangan']].reset_index(drop=True),
                checklist_df.reset_index(drop=True)
            ], axis=1)

            # Ganti kata-kata standar menjadi simbol centang agar lebih bersih dilihat
            df_final_export = df_final_export.replace({
                "Sudah": "V", "Normal": "V", "Baik": "V", 
                "Lancar": "V", "Bersih": "V", "Ya": "V", "Berfungsi Baik": "V"
            })

            st.write("---")
            st.write("### 📋 Preview Laporan Siap Cetak")
            # Tampilkan tabel yang sudah rapi di aplikasi
            st.dataframe(df_final_export, use_container_width=True)
            
            # Tombol Download data yang sudah rapi
            csv_ready = df_final_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Laporan Profesional (CSV)",
                data=csv_ready,
                file_name=f"Laporan_ME_Profesional_{d_mulai}_sd_{d_selesai}.csv",
                mime='text/csv',
                key="btn_download_rapi"
            )
        else:
            st.warning("Tidak ada data pada rentang tanggal/aset tersebut.")
    else:
        st.info("Belum ada data laporan rutin yang tersimpan.")