import streamlit as st
from supabase import create_client, Client
import datetime

# --- CONFIG & KONEKSI ---
st.set_page_config(page_title="ME Monitoring BI", layout="centered")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

st.title("🏢 Monitoring ME - BI Balikpapan")
st.info("Module 1: Checklist Pemeliharaan Spesifik SOW")

# --- FUNGSI DATA ---
def get_assets():
    query = supabase.table("assets").select("id, nama_aset, kategori, kode_qr").execute()
    return query.data

# --- DEFINISI CHECKLIST SOW ---
def render_checklist(nama_aset):
    st.write("### 🛠 Parameter Checklist SOW")
    data_checklist = {}
    
    # Logic penentuan form berdasarkan nama aset
    if "Chiller" in nama_aset:
        data_checklist['Kelistrikan'] = st.selectbox("Sistem Kelistrikan", ["OK", "Perlu Pengecekan"])
        data_checklist['Sirip Kondensor'] = st.selectbox("Sirip Kondensor", ["Bersih", "Kotor/Perlu Cuci"])
        data_checklist['Oli & Freon'] = st.selectbox("Oli & Freon", ["Cukup/Normal", "Kurang"])
        data_checklist['Arus Kompresor (A)'] = st.number_input("Arus Kompresor (Ampere)", min_value=0.0)
        
    elif "AHU" in nama_aset:
        data_checklist['Filter Udara'] = st.selectbox("Filter Udara", ["Sudah Dicuci", "Kotor"])
        data_checklist['Thermostat'] = st.radio("Thermostat ON/OFF", ["Normal", "Abnormal"])
        data_checklist['V-Belt & Bearing'] = st.selectbox("V-Belt & Bearing", ["Kondisi Baik", "Perlu Penggantian"])
        data_checklist['Temp Air In/Out'] = st.text_input("Temperatur Air In/Out (°C)")

    elif "AC" in nama_aset:
        data_checklist['Filter & Evaporator'] = st.selectbox("Filter & Evaporator", ["Bersih", "Perlu Cuci"])
        data_checklist['Drainase'] = st.radio("Saluran Drainase", ["Lancar", "Tersumbat"])
        data_checklist['Suhu Dingin'] = st.radio("Kondisi Pendinginan", ["Sangat Dingin", "Kurang Dingin"])
        data_checklist['Arus Listrik (A)'] = st.number_input("Arus Listrik (Ampere)", min_value=0.0)

    elif "Genset" in nama_aset:
        data_checklist['Kondisi Accu'] = st.selectbox("Accu & Air Accu", ["Baik", "Lemah/Perlu Tambah"])
        data_checklist['Filter Solar/Oli'] = st.selectbox("Filter Solar & Oli", ["Bersih", "Perlu Ganti"])
        data_checklist['Sistem Pembuangan'] = st.radio("Asap Buang", ["Normal", "Hitam/Tebal"])
        data_checklist['Radiator'] = st.selectbox("Kondisi Radiator", ["Bersih/Cukup", "Kotor/Kurang"])

    elif "UPS" in nama_aset:
        data_checklist['Tegangan Baterai'] = st.text_input("Tegangan Baterai (V)")
        data_checklist['Beban Output'] = st.text_input("Beban Daya Output (%)")
        data_checklist['Display UPS'] = st.radio("Kondisi Display", ["Normal", "Alarm/Error"])

    elif "Panel" in nama_aset or "Kubikel" in nama_aset:
        data_checklist['Kebersihan Wiring'] = st.selectbox("Kebersihan & Wiring", ["Rapi/Bersih", "Kotor/Berantakan"])
        data_checklist['Lampu Indikator'] = st.radio("Lampu Indikator", ["Menyala Semua", "Ada Yang Mati"])
        data_checklist['Uji Fungsi'] = st.selectbox("Uji Fungsi (Manual/Auto)", ["Berhasil", "Gagal"])

    else:
        st.write("Parameter umum untuk aset ini:")
        data_checklist['Catatan Umum'] = st.text_area("Detail Pengecekan")

    return data_checklist

# --- FORM UTAMA ---
asset_data = get_assets()
asset_options = {f"{item['kode_qr']} - {item['nama_aset']}": item['id'] for item in asset_data}

with st.form("main_form"):
    pilihan_label = st.selectbox("Pilih Aset (Berdasarkan Kode QR)", options=list(asset_options.keys()))
    nama_teknisi = st.text_input("Nama Teknisi")
    
    # Panggil fungsi checklist dinamis
    hasil_checklist = render_checklist(pilihan_label)
    
    st.write("---")
    kondisi_umum = st.radio("Kesimpulan Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
    keterangan_tambahan = st.text_area("Keterangan Tambahan / Tindakan")
    foto_ambil = st.camera_input("Ambil Foto Bukti")
    
    submit = st.form_submit_button("Simpan Laporan SOW")

    if submit:
        if nama_teknisi:
            # 1. Upload Foto jika ada
            url_foto = None
            if foto_ambil:
                fname = f"SOW_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                supabase.storage.from_("foto_maintenance").upload(fname, foto_ambil.getvalue())
                url_foto = supabase.storage.from_("foto_maintenance").get_public_url(fname)
            
            # 2. Simpan ke Database
            entry = {
                "asset_id": asset_options[pilihan_label],
                "teknisi": nama_teknisi,
                "kondisi": kondisi_umum,
                "keterangan": keterangan_tambahan,
                "foto_url": url_foto,
                "checklist_data": hasil_checklist # Menyimpan data teknis SOW
            }
            
            supabase.table("maintenance_logs").insert(entry).execute()
            st.success(f"Berhasil! Data {pilihan_label} telah diverifikasi sesuai SOW.")
            st.balloons()
        else:
            st.error("Nama Teknisi wajib diisi!")