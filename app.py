import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px
import time

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP ME BI BPP", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. MASTER SOW DINAMIS ---
SOW_MASTER = {
    "AC": {
        "Harian": ["Suhu Ruangan (°C)", "Cek suara abnormal outdoor", "Cek kebocoran air indoor"],
        "Mingguan": ["Arus Motor Fan (Ampere)", "Pembersihan filter udara", "Cek kondisi remote"],
        "Bulanan": ["Tekanan Freon (Psi)", "Cuci evaporator", "Cek arus total (Ampere)"]
    },
    "AHU": {
        "Harian": ["Cek tekanan udara (Pa)", "Cek suara bearing motor", "Cek kondisi V-Belt"],
        "Mingguan": ["Pembersihan pre-filter", "Cek drain pan", "Arus motor (Ampere)"],
        "Bulanan": ["Cek motor damper", "Cleaning coil", "Inspeksi panel kontrol"]
    },
    "BAS": {
        "Harian": ["Cek koneksi controller", "Suhu monitoring pusat (°C)", "Log alarm aktif"],
        "Mingguan": ["Cek sensor kelembaban", "Fungsi jadwal otomatis", "Backup data log harian"],
        "Bulanan": ["Kalibrasi sensor suhu", "Update software controller", "Cek hardware server"]
    },
    "GENSET": {
        "Harian": ["Bahan Bakar (%)", "Level Oli", "Tegangan Baterai (Volt)"],
        "Mingguan": ["Suhu saat Running (°C)", "Uji pemanasan (Menit)", "Cek kebocoran"],
        "Bulanan": ["Tegangan Output (Volt)", "Frekuensi (Hz)", "Cek sistem proteksi"]
    },
    "UPS": {
        "Harian": ["Kapasitas Baterai (%)", "Tegangan Input (Volt)", "Indikator Lampu"],
        "Mingguan": ["Tegangan Output (Volt)", "Suhu Battery Pack (°C)", "Cek Fan"],
        "Bulanan": ["Uji Discharge (Menit)", "Kekencangan terminal", "Laporan Load"]
    },
    "PANEL": {
        "Harian": ["Lampu indikator", "Suara dengung", "Suhu ruangan panel"],
        "Mingguan": ["Kekencangan baut", "Fungsi MCB", "Pembersihan debu"],
        "Bulanan": ["Pengukuran beban (Ampere)", "Cek grounding", "Thermography"]
    },
    "UMUM": {
        "Harian": ["Kebersihan unit", "Fungsi operasional"],
        "Mingguan": ["Pemeriksaan fisik"],
        "Bulanan": ["Catatan performa bulanan"]
    }
}

# --- 3. CSS CUSTOM ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background: #0f172a; }
    .main-header { 
        text-align: center; padding: 20px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
        border-bottom: 3px solid #38bdf8; border-radius: 0 0 20px 20px; margin-bottom: 20px; 
    }
    .main-header h1 { color: #38bdf8; margin: 0; font-size: 1.6rem; font-weight: 800; }
    .stat-card { background: #1e293b; border-radius: 12px; padding: 15px; border-bottom: 3px solid #38bdf8; text-align: center; }
    div.stButton > button { 
        width: 100%; height: 50px !important; background: #1e293b !important; 
        border: 1px solid #334155 !important; border-radius: 10px !important; 
        color: #f8fafc !important; font-weight: bold !important;
    }
    div.stButton > button:hover { border-color: #38bdf8 !important; }
    div[data-testid="stForm"] { background: #1e293b; border-radius: 15px; padding: 20px; border: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. HEADER ---
st.markdown("""
    <div class="main-header">
        <h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1>
        <p style="color:#94a3b8; font-size:0.85rem; margin-top:5px;">Sistem Informasi Monitoring Aset & Pemeliharaan Terpadu Fasilitas Mechanical Electrical</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. FUNGSI ---
@st.cache_data(ttl=30)
def load_data():
    # Limit 200 supaya semua 98 aset terambil semua
    a = supabase.table("assets").select("*").order("nama_aset").limit(200).execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
staff_map = {s['nama']: s for s in staff_list}
opt_asset = {f"[{a['kode_qr']}] {a['nama_aset']}": a for a in assets_list}
list_tek = [s['nama'] for s in staff_list if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_list if s['kategori'] == 'PEGAWAI']

def upload_foto(file):
    if file:
        fname = f"public/{uuid.uuid4()}.jpg"
        try:
            supabase.storage.from_("foto_maintenance").upload(fname, file.getvalue(), {"content-type":"image/jpeg"})
            return f"{URL}/storage/v1/object/public/foto_maintenance/{fname}"
        except: return None
    return None

# --- 6. LOGIKA HALAMAN ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
def pindah(n): st.session_state.hal = n

# --- MENU UTAMA ---
if st.session_state.hal == 'Menu':
    g_open = supabase.table("gangguan_logs").select("id").eq("status", "Open").execute().data
    m_today = supabase.table("maintenance_logs").select("id").filter("created_at", "gte", datetime.date.today().isoformat()).execute().data
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="stat-card"><small>GANGGUAN</small><br><b style="color:#ef4444; font-size:1.5rem;">{len(g_open)}</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card"><small>CEK HARI INI</small><br><b style="color:#22c55e; font-size:1.5rem;">{len(m_today)}</b></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card"><small>TOTAL ASET</small><br><b style="color:#38bdf8; font-size:1.5rem;">{len(assets_list)}</b></div>', unsafe_allow_html=True)
    
    st.write("")
    with st.expander("🕒 3 AKTIVITAS TERAKHIR TEKNISI"):
        recent = supabase.table("maintenance_logs").select("teknisi, periode, created_at, assets(nama_aset)").order("created_at", desc=True).limit(3).execute().data
        if recent:
            for r in recent:
                tgl = pd.to_datetime(r['created_at']).strftime('%H:%M')
                st.caption(f"📌 **{tgl}** - {r['teknisi']} selesai cek {r['assets']['nama_aset']} ({r['periode']})")
        else: st.caption("Belum ada aktivitas hari ini.")

    st.write("---")
    cl, cr = st.columns(2)
    with cl:
        if st.button("☀️ HARIAN"): pindah('Harian'); st.rerun()
        if st.button("📅 MINGGUAN"): pindah('Mingguan'); st.rerun()
        if st.button("🏆 BULANAN"): pindah('Bulanan'); st.rerun()
    with cr:
        if st.button("⚠️ GANGGUAN"): pindah('Gangguan'); st.rerun()
        if st.button("🔄 UPDATE"): pindah('Update'); st.rerun()
        if st.button("📑 LAPORAN"): pindah('Export'); st.rerun()

# --- HALAMAN CHECKLIST ---
elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"📋 Checklist {st.session_state.hal}")
    
    list_kat = ["SEMUA", "AC", "AHU", "UPS", "BAS", "PANEL", "GENSET", "UMUM"]
    kat_filter = st.pills("Pilih Kelompok Aset:", list_kat, default="SEMUA") 
    
    if kat_filter == "SEMUA":
        list_pilihan = list(opt_asset.keys())
    else:
        # Filter akurat dengan membersihkan spasi
        list_pilihan = [k for k, v in opt_asset.items() if str(v.get('kategori')).strip().upper() == kat_filter.upper()]

    if not list_pilihan:
        st.info(f"💡 Belum ada aset di kategori {kat_filter}.")
    else:
        sel_a = st.selectbox(f"Pilih Unit ({len(list_pilihan)} Unit):", list_pilihan)
        asset_data = opt_asset[sel_a]
        
        k_db = str(asset_data.get('kategori')).strip().upper()
        k_key = k_db if k_db in SOW_MASTER else "UMUM"
        
        with st.form("f_chk_final"):
            tek = st.selectbox("Teknisi", list_tek)
            res_list = []
            for i, task in enumerate(SOW_MASTER[k_key][st.session_state.hal]):
                if any(x in task.upper() for x in ["%", "VOLT", "AMPERE", "PSI", "°C", "HZ", "PA"]):
                    val = st.number_input(task, step=0.1, key=f"v_{i}")
                    res_list.append(f"{task}: {val}")
                else:
                    r = st.radio(task, ["Normal", "Abnormal", "N/A"], horizontal=True, key=f"r_{i}")
                    res_list.append(f"{task}: {r}")
            
            kon = st.select_slider("Kondisi Akhir", ["Rusak", "Perlu Perbaikan", "Baik", "Sangat Baik"], "Baik")
            cat = st.text_area("Catatan")
            if st.form_submit_button("💾 SIMPAN DATA"):
                ket_f = " | ".join(res_list) + (f" | Catatan: {cat}" if cat else "")
                supabase.table("maintenance_logs").insert({
                    "asset_id": asset_data['id'], "teknisi": tek, "periode": st.session_state.hal, "kondisi": kon, "keterangan": ket_f
                }).execute()
                st.success("✅ Tersimpan!"); time.sleep(1); st.rerun()

# --- HALAMAN GANGGUAN ---
elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    with st.form("f_g"):
        aset = st.selectbox("Pilih Aset", list(opt_asset.keys()))
        pel = st.selectbox("Pelapor", list_tek)
        urg = st.select_slider("Urgensi", ["Rendah", "Sedang", "Tinggi", "Darurat"])
        mas = st.text_area("Masalah")
        foto = st.camera_input("Foto")
        if st.form_submit_button("🚨 KIRIM"):
            u = upload_foto(foto)
            supabase.table("gangguan_logs").insert({
                "asset_id": opt_asset[aset]['id'], "teknisi": pel, "masalah": mas, "urgensi": urg, "status": "Open", "foto_kerusakan_url": u
            }).execute()
            st.warning("Terkirim!"); time.sleep(1); st.rerun()

# --- HALAMAN UPDATE ---
elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    logs = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if logs:
        for l in logs:
            with st.expander(f"⚠️ {l['assets']['nama_aset']}"):
                sol = st.text_area("Tindakan", key=f"s_{l['id']}")
                if st.button("Selesai", key=f"b_{l['id']}"):
                    supabase.table("gangguan_logs").update({"status":"Closed", "tindakan_perbaikan":sol, "tgl_perbaikan":datetime.datetime.now().isoformat()}).eq("id", l['id']).execute()
                    st.success("Berhasil!"); time.sleep(1); st.rerun()
    else: st.info("Tidak ada pending perbaikan.")