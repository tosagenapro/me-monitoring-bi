import streamlit as st
from supabase import create_client
import datetime

# --- KONEKSI ---
URL = "https://yuvnwzzvapasxfqzmqme.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl1dm53enp2YXBhc3hmcXptcW1lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNzEzMDQsImV4cCI6MjA4Njk0NzMwNH0._KG8wlwxT9sSlCKmnyjALgjHF3tRnEWIy3fk4sCYpA8"
supabase = create_client(URL, KEY)

st.title("🏢 ME Monitoring - BI Balikpapan")

# --- AMBIL DATA ASET ---
def get_assets():
    return supabase.table("assets").select("*").execute().data

data_aset = get_assets()

# --- TAMPILAN ---
st.write("### 🛠️ Menu Pemeriksaan")

if data_aset:
    # Pilih aset yang mau diperiksa
    nama_aset_list = [a['nama_aset'] for a in data_aset]
    pilihan = st.selectbox("Pilih Alat yang akan dicek:", nama_aset_list)
    
    # Ambil detail aset yang dipilih
    detail_aset = next(a for a in data_aset if a['nama_aset'] == pilihan)
    
    st.info(f"Memeriksa: **{detail_aset['nama_aset']}** | Lokasi: {detail_aset['lokasi']}")

    # --- FORM CHECKLIST (Sesuai SOW) ---
    with st.form("form_pemeriksaan"):
        st.write("**Parameter Pemeriksaan:**")
        kondisi = st.radio("Kondisi Alat:", ["Normal", "Perlu Perbaikan", "Rusak"])
        catatan = st.text_area("Catatan/Temuan di Lapangan:")
        
        # FITUR GANDA: Bisa Kamera (untuk HP) atau Upload File (untuk Laptop)
        foto_kamera = st.camera_input("Ambil Foto (Gunakan HP)")
        foto_upload = st.file_uploader("Atau Upload Gambar dari Laptop", type=['jpg', 'jpeg', 'png'])
        
        # Pilih salah satu foto yang ada
        foto_final = foto_kamera if foto_kamera else foto_upload
        
        submit = st.form_submit_button("Simpan Laporan")
        
        if submit:
            path_foto = ""
            if foto_final:
                # Simpan foto ke Supabase Storage
                nama_file = f"{detail_aset['id']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                storage_response = supabase.storage.from_("foto_maintenance").upload(nama_file, foto_final.getvalue())
                path_foto = supabase.storage.from_("foto_maintenance").get_public_url(nama_file)

            data_laporan = {
                "asset_id": detail_aset['id'],
                "status": kondisi,
                "catatan": catatan,
                "foto_url": path_foto
            }
            
            try:
                supabase.table("maintenance_logs").insert(data_laporan).execute()
                st.success("✅ Berhasil! Laporan tersimpan.")
            except Exception as e:
                st.error(f"Gagal: {e}")
# --- HALAMAN REKAP (Di bawah Form) ---
st.divider()
st.write("### 📜 Rekap Laporan Maintenance Terbaru")

def get_logs():
    # Mengambil data laporan terbaru
    return supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).limit(10).execute().data

logs = get_logs()
if logs:
    for log in logs:
        with st.expander(f"📅 {log['created_at'][:10]} - {log['assets']['nama_aset']} ({log['status']})"):
            st.write(f"**Catatan:** {log['catatan']}")
            if log['foto_url']:
                st.image(log['foto_url'], caption="Foto Temuan", width=300)
else:
    st.info("Belum ada riwayat laporan.")