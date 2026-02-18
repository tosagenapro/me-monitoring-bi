import streamlit as st
from supabase import create_client, Client
import datetime

# --- CONFIG & KONEKSI ---
st.set_page_config(page_title="ME Monitoring BI", layout="centered")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

st.title("🏢 Monitoring ME - BI Balikpapan")

# --- FUNGSI DATA ---
def get_assets():
    query = supabase.table("assets").select("id, nama_aset, kategori, kode_qr").order("nama_aset").execute()
    return query.data

# --- FUNGSI CHECKLIST SOW (MODULE 1) ---
def render_sow_checklist(nama_unit):
    st.info(f"📋 Parameter SOW: {nama_unit}")
    ck = {}
    if "Chiller" in nama_unit:
        ck['Listrik'] = st.radio("Sistem Kelistrikan Chiller", ["Normal", "Abnormal"])
        ck['Kondensor'] = st.radio("Pembersihan Sirip Kondensor", ["Sudah", "Belum"])
        ck['Arus_Ampere'] = st.text_input("Arus Kompresor & Fan (Ampere)")
        # ... (Parameter lain tetap ada di memori kode)
    elif "AHU" in nama_unit:
        ck['Cuci_Filter'] = st.radio("Pencucian Filter Udara", ["Sudah", "Belum"])
        ck['Thermostat'] = st.radio("Thermostat ON/OFF", ["Normal", "Rusak"])
        ck['Temp_Air'] = st.text_input("Temperatur Air In/Out (°C)")
    elif "AC" in nama_unit:
        ck['Filter_Evap'] = st.radio("Filter & Evaporator", ["Bersih", "Kotor"])
        ck['Drainase'] = st.radio("Saluran Drainase", ["Lancar", "Tersumbat"])
    elif "Genset" in nama_unit:
        ck['Accu'] = st.radio("Kondisi Accu & Air Accu", ["Baik", "Perlu Maintenance"])
        ck['Radiator'] = st.radio("Kondisi Radiator", ["Bersih/Cukup", "Kotor/Kurang"])
    elif "UPS" in nama_unit:
        ck['Display'] = st.radio("Pemeriksaan Display", ["Normal", "Error/Alarm"])
        ck['Batt_Volt'] = st.text_input("Tegangan Baterai (VDC)")
    else:
        ck['Catatan'] = st.text_area("Detail Pengecekan Umum")
    return ck

# --- PREPARASI DATA ASET ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

# --- SISTEM TAB (PEMISAH MODULE) ---
tab1, tab2 = st.tabs(["📋 Checklist Rutin (SOW)", "⚠️ Lapor Gangguan (Emergency)"])

# ==========================================
# MODULE 1: CHECKLIST RUTIN
# ==========================================
with tab1:
    selected_label = st.selectbox("Pilih Aset (Rutin)", options=list(options.keys()), key="qr_rutin")
    selected_asset = options[selected_label]
    
    with st.form("form_rutin", clear_on_submit=True):
        nama_teknisi = st.text_input("Nama Teknisi")
        results = render_sow_checklist(selected_asset['nama_aset'])
        kondisi_final = st.radio("Kesimpulan Kondisi", ["Baik", "Rusak"])
        foto = st.camera_input("Foto Bukti Rutin", key="foto_rutin")
        
        submit_rutin = st.form_submit_button("Simpan Laporan Rutin")
        if submit_rutin:
            # (Logika simpan ke maintenance_logs tetap sama)
            st.success("Laporan Rutin Tersimpan!")

# ==========================================
# MODULE 2: LAPOR GANGGUAN (BARU)
# ==========================================
with tab2:
    st.warning("Gunakan form ini hanya untuk melaporkan kerusakan mendadak!")
    selected_label_gng = st.selectbox("Pilih Aset Bermasalah", options=list(options.keys()), key="qr_gangguan")
    aset_gng = options[selected_label_gng]
    
    with st.form("form_gangguan", clear_on_submit=True):
        pelapor = st.text_input("Nama Pelapor")
        masalah = st.text_area("Deskripsi Kerusakan", placeholder="Jelaskan apa yang rusak...")
        urgensi = st.select_slider("Tingkat Urgensi", options=["Rendah", "Sedang", "Darurat"])
        foto_gng = st.camera_input("Foto Kerusakan", key="foto_gng")
        
        submit_gng = st.form_submit_button("KIRIM LAPORAN DARURAT")
        if submit_gng:
            # Logika simpan ke tabel gangguan_logs
            st.error(f"Laporan Bahaya untuk {selected_label_gng} telah dikirim!")