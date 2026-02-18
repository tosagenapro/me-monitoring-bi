import streamlit as st
from supabase import create_client, Client
import datetime

# Konfigurasi Halaman
st.set_page_config(page_title="ME Monitoring BI Balikpapan", layout="centered")

# Inisialisasi Koneksi Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

st.title("🏢 Monitoring Maintenance ME")
st.subheader("Bank Indonesia Balikpapan")

# --- FUNGSI AMBIL DATA ---
def get_assets():
    query = supabase.table("assets").select("id, nama_aset").execute()
    return query.data

def get_logs():
    query = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).limit(10).execute()
    return query.data

# --- FORM INPUT ---
with st.form("maintenance_form", clear_on_submit=True):
    st.write("### Input Laporan Baru")
    
    asset_data = get_assets()
    asset_options = {item['nama_aset']: item['id'] for item in asset_data}
    
    pilihan_aset = st.selectbox("Pilih Aset", options=list(asset_options.keys()))
    nama_teknisi = st.text_input("Nama Teknisi")
    kondisi = st.radio("Kondisi Aset", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"])
    keterangan = st.text_area("Keterangan Tambahan")
    
    st.write("### Foto Kondisi Aset")
    foto_ambil = st.camera_input("Ambil Foto")
    
    submit = st.form_submit_button("Kirim Laporan")

    if submit:
        if nama_teknisi:
            url_foto_final = None
            
            # PROSES UPLOAD FOTO (Jika ada)
            if foto_ambil:
                nama_file = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                try:
                    # Simpan ke Storage Bucket
                    supabase.storage.from_("foto_maintenance").upload(nama_file, foto_ambil.getvalue())
url_foto_final = supabase.storage.from_("foto_maintenance").get_public_url(nama_file)
                except Exception as e:
                    st.error(f"Gagal upload foto: {e}")

            # SIMPAN DATA KE TABEL
            data_input = {
                "asset_id": asset_options[pilihan_aset],
                "teknisi": nama_teknisi,
                "kondisi": kondisi,
                "keterangan": keterangan,
                "foto_url": url_foto_final # Link foto disimpan di sini
            }
            try:
                supabase.table("maintenance_logs").insert(data_input).execute()
                st.success(f"Berhasil mengirim laporan untuk {pilihan_aset}!")
                st.balloons()
            except Exception as e:
                st.error(f"Gagal mengirim data: {e}")
        else:
            st.warning("Mohon isi nama teknisi!")

# --- TABEL REKAP ---
st.write("---")
st.write("### 📋 10 Laporan Terakhir")
logs = get_logs()

if logs:
    rekap_data = []
    for log in logs:
        # Menampilkan link gambar jika ada
        link_gambar = f"[Lihat Foto]({log['foto_url']})" if log.get('foto_url') else "Tanpa Foto"
        rekap_data.append({
            "Waktu": log['created_at'].split('T')[0],
            "Aset": log['assets']['nama_aset'] if log['assets'] else "N/A",
            "Teknisi": log['teknisi'],
            "Kondisi": log['kondisi'],
            "Bukti": link_gambar
        })
    # Menggunakan st.dataframe agar link bisa diklik
    st.dataframe(rekap_data)