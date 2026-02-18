import streamlit as st
from supabase import create_client, Client
import datetime

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
    # Ambil laporan gangguan yang statusnya belum 'Resolved'
    query = supabase.table("gangguan_logs").select("*, assets(nama_aset, kode_qr)").neq("status", "Resolved").execute()
    return query.data

# --- FUNGSI CHECKLIST SOW ---
def render_sow_checklist(nama_unit):
    st.info(f"📋 Parameter SOW: {nama_unit}")
    ck = {}
    if "Chiller" in nama_unit:
        ck['Listrik'] = st.radio("Sistem Kelistrikan", ["Normal", "Abnormal"])
        ck['Arus_Ampere'] = st.text_input("Arus Kompresor (Ampere)")
    elif "AHU" in nama_unit:
        ck['Filter'] = st.radio("Kebersihan Filter", ["Bersih", "Kotor"])
        ck['Temp'] = st.text_input("Suhu Udara Keluar (°C)")
    elif "Genset" in nama_unit:
        ck['Accu'] = st.radio("Kondisi Accu", ["Baik", "Maintenance"])
        ck['Solar'] = st.text_input("Level Bahan Bakar (%)")
    else:
        ck['Kondisi'] = st.radio("Status Unit", ["Normal", "Pengecekan"])
    return ck

# --- PREPARASI ---
asset_data = get_assets()
options = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in asset_data}

# --- SISTEM TAB ---
tab1, tab2, tab3 = st.tabs(["📋 Checklist Rutin", "⚠️ Lapor Gangguan", "✅ Update Perbaikan"])

# ==========================================
# TAB 1: RUTIN
# ==========================================
with tab1:
    sel_rutin = st.selectbox("Pilih Aset", options=list(options.keys()), key="r1")
    with st.form("f_rutin"):
        nama = st.text_input("Nama Teknisi")
        res = render_sow_checklist(options[sel_rutin]['nama_aset'])
        f_rutin = st.camera_input("Foto Bukti", key="f1")
        if st.form_submit_button("Simpan"):
            st.success("Data Tersimpan!")

# ==========================================
# TAB 2: LAPOR GANGGUAN
# ==========================================
with tab2:
    sel_gng = st.selectbox("Aset Bermasalah", options=list(options.keys()), key="g2")
    with st.form("f_gangguan"):
        pelapor = st.text_input("Nama Pelapor")
        masalah = st.text_area("Detail Kerusakan")
        urgensi = st.select_slider("Urgensi", options=["Rendah", "Sedang", "Darurat"])
        f_gng = st.camera_input("Foto Kerusakan", key="f2")
        if st.form_submit_button("Kirim Laporan"):
            if pelapor and masalah:
                url = None
                if f_gng:
                    fn = f"GNG_{datetime.datetime.now().strftime('%H%M%S')}.jpg"
                    supabase.storage.from_("foto_maintenance").upload(fn, f_gng.getvalue())
                    url = supabase.storage.from_("foto_maintenance").get_public_url(fn)
                supabase.table("gangguan_logs").insert({
                    "asset_id": options[sel_gng]['id'], "teknisi": pelapor,
                    "masalah": masalah, "urgensi": urgensi, "foto_kerusakan_url": url
                }).execute()
                st.error("Laporan Dikirim!")

# ==========================================
# TAB 3: UPDATE PERBAIKAN (NEW!)
# ==========================================
with tab3:
    st.subheader("Penyelesaian Laporan Kerusakan")
    issues = get_open_issues()
    
    if not issues:
        st.info("Alhamdulillah, saat ini tidak ada laporan kerusakan aktif.")
    else:
        # Buat pilihan laporan yang mau di-update
        issue_options = {f"[{i['urgensi']}] {i['assets']['nama_aset']} - {i['masalah'][:30]}...": i for i in issues}
        sel_issue_label = st.selectbox("Pilih Laporan untuk Diselesaikan", options=list(issue_options.keys()))
        issue_data = issue_options[sel_issue_label]
        
        st.write(f"**Detail Masalah:** {issue_data['masalah']}")
        st.write(f"**Dilaporkan Oleh:** {issue_data['teknisi']} ({issue_data['created_at'][:10]})")
        
        with st.form("f_perbaikan"):
            t_perbaikan = st.text_input("Nama Teknisi Perbaikan")
            tindakan = st.text_area("Tindakan yang Dilakukan (Kronologi)")
            f_after = st.camera_input("Foto Bukti Selesai (After)", key="f3")
            
            if st.form_submit_button("Update Menjadi SELESAI (Resolved)"):
                if t_perbaikan and tindakan:
                    url_after = None
                    if f_after:
                        fn_a = f"FIX_{datetime.datetime.now().strftime('%H%M%S')}.jpg"
                        supabase.storage.from_("foto_maintenance").upload(fn_a, f_after.getvalue())
                        url_after = supabase.storage.from_("foto_maintenance").get_public_url(fn_a)
                    
                    # UPDATE DATA DI SUPABASE
                    supabase.table("gangguan_logs").update({
                        "status": "Resolved",
                        "tindakan_perbaikan": tindakan,
                        "teknisi_perbaikan": t_perbaikan,
                        "tgl_perbaikan": datetime.datetime.now().isoformat(),
                        "foto_setelah_perbaikan_url": url_after
                    }).eq("id", issue_data['id']).execute()
                    
                    st.success("Status Aset kembali NORMAL (Resolved)!")
                    st.balloons()
                else:
                    st.warning("Mohon isi nama teknisi dan tindakan perbaikan.")