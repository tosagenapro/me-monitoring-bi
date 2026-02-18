import streamlit as st
from supabase import create_client, Client
import datetime

# --- CONFIG ---
st.set_page_config(page_title="ME Monitoring BI", layout="centered")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

st.title("🏢 Monitoring ME - BI Balikpapan")
st.markdown("---")

# --- FUNGSI AMBIL DATA ---
def get_assets():
    # Ambil data dan urutkan berdasarkan nama agar tidak berantakan
    query = supabase.table("assets").select("id, nama_aset, kategori, kode_qr").order("nama_aset").execute()
    return query.data

# --- MODUL CHECKLIST SOW LENGKAP ---
def render_sow_checklist(nama_unit):
    st.info(f"📋 Form Checklist: {nama_unit}")
    ck = {}
    
    if "Chiller" in nama_unit:
        ck['Listrik'] = st.radio("Sistem Kelistrikan Chiller", ["Normal", "Abnormal"])
        ck['Kondensor'] = st.radio("Pembersihan Sirip Kondensor", ["Sudah", "Belum"])
        ck['Oli_Freon'] = st.radio("Oli & Freon (Sesuai Standar)", ["Ya", "Tidak"])
        ck['Pompa_Fan'] = st.radio("Chiller Fan & Pompa Sirkulasi", ["Baik", "Abnormal"])
        ck['Valve'] = st.radio("Kondisi Semua Valve", ["Berfungsi Baik", "Macet/Rusak"])
        ck['Arus_Ampere'] = st.text_input("Arus Kompresor & Fan (Ampere)")
        ck['Korosi'] = st.radio("Pengecekan Body (Anti Korosi)", ["Aman", "Ada Karat"])
        ck['Running_Test'] = st.radio("Proses Running/Off Mesin", ["Normal", "Ada Kendala"])

    elif "Cooling Tower" in nama_unit:
        ck['Belt_Fan'] = st.radio("Tension Belt & Motor Fan", ["OK", "Perlu Setel"])
        ck['Clogging'] = st.radio("Pembersihan Basin/Filler (Clogging)", ["Lancar", "Ada Sumbatan"])
        ck['Lumpur'] = st.radio("Lower Basin (Lumpur/Kotoran)", ["Bersih", "Kotor"])

    elif "AHU" in nama_unit:
        ck['Cuci_Filter'] = st.radio("Pencucian Filter Udara", ["Sudah", "Belum"])
        ck['Stop_Valve'] = st.radio("Stop Valve In/Out", ["Baik", "Bocor/Macet"])
        ck['Thermostat'] = st.radio("Thermostat ON/OFF", ["Normal", "Rusak"])
        ck['Mekanis'] = st.radio("V-Belt, Bearing, Mounting", ["Kondisi Baik", "Perlu Perbaikan"])
        ck['Listrik_AHU'] = st.text_input("Tegangan & Arus Motor")
        ck['Pressure_Gauge'] = st.text_input("Water Pressure Gauge (In/Out)")
        ck['Temp_Air'] = st.text_input("Temperatur Air (°C)")
        ck['Strainer'] = st.radio("Pengecekan Strainer Air", ["Bersih", "Kotor"])

    elif "AC" in nama_unit:
        ck['Listrik_AC'] = st.radio("Sistem Kelistrikan", ["Normal", "Abnormal"])
        ck['Filter_Evap'] = st.radio("Filter & Evaporator (Sirip)", ["Bersih", "Kotor"])
        ck['Blower'] = st.radio("Blower Indoor/Outdoor", ["Bersih/Normal", "Berisik/Kotor"])
        ck['Drainase'] = st.radio("Saluran Drainase (Bak Air)", ["Lancar", "Tersumbat"])
        ck['Kondensor_AC'] = st.radio("Pembersihan Kondensor", ["Sudah", "Belum"])
        ck['Uji_Fungsi'] = st.text_area("Hasil Uji (Suhu, Aliran Udara, Suara)")

    elif "Genset" in nama_unit:
        ck['Accu'] = st.radio("Kondisi Accu & Air Accu", ["Baik", "Perlu Maintenance"])
        ck['Radiator'] = st.radio("Kondisi Radiator", ["Bersih/Cukup", "Kotor/Kurang"])
        ck['Bahan_Bakar'] = st.radio("Sistem Pipa & Injeksi BBM", ["Aman/Tidak Bocor", "Ada Rembesan"])
        ck['Filter_Solar_Oli'] = st.radio("Kondisi Filter Solar/Oli", ["Baik", "Perlu Ganti"])
        ck['Pembuangan'] = st.radio("Sistem Gas Buang", ["Normal", "Bermasalah"])

    elif "UPS" in nama_unit:
        ck['Display'] = st.radio("Pemeriksaan Display", ["Normal", "Error/Alarm"])
        ck['Input_Volt'] = st.text_input("Input Listrik (Volt)")
        ck['Batt_Volt'] = st.text_input("Tegangan Baterai (VDC)")
        ck['Load'] = st.text_input("Beban Daya Output (%)")

    elif "Panel" in nama_unit or "Kubikel" in nama_unit:
        ck['Komponen'] = st.radio("Kondisi MCB, Busbar, Lampu Indikator", ["Lengkap/Baik", "Bermasalah"])
        ck['Kebersihan'] = st.radio("Kebersihan Dalam/Luar Panel", ["Bersih", "Kotor"])
        ck['Proteksi'] = st.radio("Pelindung Tegangan", ["Terlindungi", "Terbuka/Bahaya"])

    else:
        ck['Catatan'] = st.text_area("Detail Pengecekan Umum")
        
    return ck

# --- FORM INPUT ---
asset_data = get_assets()
# Gabungkan Kode QR dan Nama Aset untuk label dropdown
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

with st.form("form_maintenance", clear_on_submit=True):
    selected_label = st.selectbox("1. Pilih Aset (Berdasarkan Kode QR)", options=list(options.keys()))
    selected_asset = options[selected_label]
    
    nama_teknisi = st.text_input("2. Nama Teknisi")
    
    # Render parameter SOW berdasarkan aset yang dipilih
    checklist_results = render_sow_checklist(selected_asset['nama_aset'])
    
    st.write("---")
    kondisi_final = st.radio("3. Kesimpulan Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
    tindakan = st.text_area("4. Keterangan Tambahan / Tindakan")
    
    foto = st.camera_input("5. Ambil Foto Bukti")
    
    submit = st.form_submit_button("Kirim Laporan SOW")

    if submit:
        if nama_teknisi:
            url_foto = None
            if foto:
                fn = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                supabase.storage.from_("foto_maintenance").upload(fn, foto.getvalue())
                url_foto = supabase.storage.from_("foto_maintenance").get_public_url(fn)
            
            payload = {
                "asset_id": selected_asset['id'],
                "teknisi": nama_teknisi,
                "kondisi": kondisi_final,
                "keterangan": tindakan,
                "foto_url": url_foto,
                "checklist_data": checklist_results
            }
            
            supabase.table("maintenance_logs").insert(payload).execute()
            st.success(f"Laporan {selected_label} Berhasil Disimpan!")
            st.balloons()
        else:
            st.error("Nama Teknisi tidak boleh kosong!")