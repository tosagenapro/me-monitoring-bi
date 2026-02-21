import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px
import time
from PIL import Image
import io
import requests

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP ME BI BPP", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. QR DETECTOR LOGIC ---
query_params = st.query_params
qr_code_detected = query_params.get("unit")
BASE_URL_APP = "https://simantap-bi-bpp.streamlit.app"

# --- 3. MASTER SOW ---
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
        "Harian": ["Kapasitas Baterai (%)", "Tegangan Input (Volt) ", "Indikator Lampu"],
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

# --- 4. CSS ---
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
    div.stButton > button { width: 100%; height: 60px !important; background: #1e293b !important; border-radius: 12px !important; color: #f8fafc !important; font-weight: bold !important; }
    div[data-testid="stForm"] { background: #1e293b; border-radius: 15px; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNGSI KERJA ---
@st.cache_data(ttl=30)
def load_data():
    a = supabase.table("assets").select("*").order("nama_aset").execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
staff_map = {s['nama']: s for s in staff_list}
opt_asset = {f"[{a['kode_qr']}] {a['nama_aset']}": a for a in assets_list}
qr_map = {a['kode_qr']: a for a in assets_list}
list_tek = [s['nama'] for s in staff_list if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_list if s['kategori'] == 'PEGAWAI']

def upload_foto(file):
    if file:
        try:
            img = Image.open(file).convert('RGB')
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            fname = f"{uuid.uuid4()}.jpg" # Langsung di root bucket saja
            supabase.storage.from_("foto_maintenance").upload(fname, buf.getvalue(), {"content-type":"image/jpeg"})
            return f"{URL}/storage/v1/object/public/foto_maintenance/{fname}"
        except: return None
    return None

def generate_pdf_final(df, rentang, peg, tek, judul, tipe="Maintenance"):
    try:
        pdf = FPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"{judul} - KPwBI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10); pdf.cell(0, 7, f"Periode: {rentang}", ln=True, align="C"); pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 8); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        if tipe == "Maintenance":
            w = [60, 25, 30, 25, 130]; cols = ["Nama Aset", "Periode", "Teknisi", "Kondisi", "Detail Pekerjaan"]
        else:
            w = [60, 70, 30, 30, 80]; cols = ["Nama Aset", "Masalah", "Pelapor", "Status", "Tindakan Perbaikan"]
        
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln(); pdf.set_font("Helvetica", "", 7); pdf.set_text_color(0, 0, 0)
        
        for _, row in df.iterrows():
            pdf.cell(w[0], 10, str(row.get('Nama Aset','')), 1)
            if tipe == "Maintenance":
                pdf.cell(w[1], 10, str(row.get('periode','')), 1); pdf.cell(w[2], 10, str(row.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(row.get('kondisi','')), 1); pdf.cell(w[4], 10, str(row.get('keterangan',''))[:95], 1)
            else:
                pdf.cell(w[1], 10, str(row.get('masalah',''))[:50], 1); pdf.cell(w[2], 10, str(row.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(row.get('status','')), 1); pdf.cell(w[4], 10, str(row.get('tindakan_perbaikan',''))[:60], 1)
            pdf.ln()

        # SIGNATURE
        pdf.ln(10); pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, "Known,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
        pdf.cell(138, 5, str(peg.get('posisi', 'Pegawai')).replace('"', ''), 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
        pdf.ln(18); pdf.set_font("Helvetica", "BU", 10)
        pdf.cell(138, 5, str(peg.get('nama', '')), 0, 0, "C"); pdf.cell(138, 5, str(tek.get('nama', '')), 0, 1, "C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, str(peg.get('jabatan_pdf', '')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")

        # LAMPIRAN FOTO (GANGGUAN SAJA)
        if tipe != "Maintenance":
            pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "LAMPIRAN DOKUMENTASI", ln=True, align="C"); pdf.ln(5)
            for idx, row in df.iterrows():
                urls = [row.get('foto_kerusakan_url'), row.get('foto_setelah_perbaikan_url')]
                if any(urls):
                    pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 7, f"Unit: {row['Nama Aset']}", ln=True)
                    cy = pdf.get_y()
                    for i, url in enumerate(urls):
                        if url and str(url) != "None":
                            try:
                                res = requests.get(url, timeout=10)
                                if res.status_code == 200:
                                    img_data = io.BytesIO(res.content)
                                    # FPDF butuh nama file, kita akali dengan object BytesIO tapi format tetap JPEG
                                    pdf.image(img_data, x=10 + (i*75), y=cy, w=65, type='JPG')
                                    pdf.set_xy(10 + (i*75), cy+44); pdf.cell(65, 5, "BEFORE" if i==0 else "AFTER", 0, 0, "C")
                            except: pass
                    pdf.ln(55)
                    if pdf.get_y() > 220: pdf.add_page()
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Error PDF: {e}")
        return None

# --- 6. ROUTING ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
if qr_code_detected and 'qr_handled' not in st.session_state:
    st.session_state.hal = 'LandingQR'; st.session_state.qr_handled = True

def pindah(n): st.session_state.hal = n

st.markdown("""<div class="main-header"><h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1></div>""", unsafe_allow_html=True)

# --- 7. HALAMAN ---
if st.session_state.hal == 'LandingQR':
    asset_qr = qr_map.get(qr_code_detected)
    if asset_qr:
        st.info(f"Unit: {asset_qr['nama_aset']}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("☀️ HARIAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Harian'); st.rerun()
            if st.button("📅 MINGGUAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Mingguan'); st.rerun()
        with c2:
            if st.button("🏆 BULANAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Bulanan'); st.rerun()
            if st.button("⚠️ GANGGUAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Gangguan'); st.rerun()
    else: st.error("QR Tak Dikenal"); st.button("Menu Utama", on_click=lambda: pindah('Menu'))

elif st.session_state.hal == 'Menu':
    c1, c2, c3 = st.columns(3)
    c1.metric("GANGGUAN", len(supabase.table("gangguan_logs").select("id").eq("status", "Open").execute().data))
    c2.metric("ASET", len(assets_list))
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
    if st.button("📊 STATISTIK"): pindah('Statistik'); st.rerun()

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    is_qr = 'sel_asset_qr' in st.session_state
    asset_data = st.session_state.sel_asset_qr if is_qr else opt_asset[st.selectbox("Pilih Unit:", list(opt_asset.keys()))]
    with st.form("f_chk"):
        tek = st.selectbox("Teknisi", list_tek); res_list = []
        k_key = str(asset_data.get('kategori')).strip().upper() if str(asset_data.get('kategori')).strip().upper() in SOW_MASTER else "UMUM"
        for i, task in enumerate(SOW_MASTER[k_key][st.session_state.hal]):
            if any(x in task.upper() for x in ["%", "VOLT", "AMPERE", "PSI", "°C"]):
                val = st.number_input(task, step=0.1, key=f"v_{i}"); res_list.append(f"{task}: {val}")
            else:
                r = st.radio(task, ["Normal", "Abnormal", "N/A"], horizontal=True, key=f"r_{i}"); res_list.append(f"{task}: {r}")
        kon = st.select_slider("Kondisi", ["Rusak", "Perlu Perbaikan", "Baik", "Sangat Baik"], "Baik")
        if st.form_submit_button("💾 SIMPAN"):
            supabase.table("maintenance_logs").insert({"asset_id": asset_data['id'], "teknisi": tek, "periode": st.session_state.hal, "kondisi": kon, "keterangan": " | ".join(res_list)}).execute()
            if is_qr: del st.session_state.sel_asset_qr
            st.success("Tersimpan!"); time.sleep(1); pindah('Menu'); st.rerun()
    if st.button("⬅️ BATAL"): 
        if is_qr: del st.session_state.sel_asset_qr
        pindah('Menu'); st.rerun()

elif st.session_state.hal == 'Gangguan':
    is_qr = 'sel_asset_qr' in st.session_state
    asset_data = st.session_state.sel_asset_qr if is_qr else opt_asset[st.selectbox("Pilih Aset", list(opt_asset.keys()))]
    with st.form("f_g"):
        pel = st.selectbox("Teknisi Pelapor", list_tek); mas = st.text_area("Masalah"); foto = st.camera_input("Foto Bukti")
        if st.form_submit_button("🚨 KIRIM"):
            u = upload_foto(foto)
            supabase.table("gangguan_logs").insert({"asset_id": asset_data['id'], "teknisi": pel, "masalah": mas, "urgensi": "Tinggi", "status": "Open", "foto_kerusakan_url": u}).execute()
            if is_qr: del st.session_state.sel_asset_qr
            st.warning("Terkirim!"); time.sleep(1); pindah('Menu'); st.rerun()
    if st.button("⬅️ KEMBALI"): 
        if is_qr: del st.session_state.sel_asset_qr
        pindah('Menu'); st.rerun()

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    logs = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    for l in logs:
        with st.expander(f"⚠️ {l['assets']['nama_aset']}"):
            with st.form(f"f_up_{l['id']}"):
                sol = st.text_area("Tindakan"); f_up = st.camera_input("Foto Selesai")
                if st.form_submit_button("Selesai"):
                    u_f = upload_foto(f_up)
                    supabase.table("gangguan_logs").update({"status":"Closed", "tindakan_perbaikan":sol, "tgl_perbaikan":datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url":u_f}).eq("id", l['id']).execute()
                    st.success("Berhasil!"); time.sleep(1); st.rerun()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    tipe_lap = st.radio("Tipe:", ["Checklist Maintenance", "Log Gangguan & Perbaikan"], horizontal=True)
    dr = st.date_input("Rentang", [datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()])
    if len(dr) == 2:
        tbl = "maintenance_logs" if "Checklist" in tipe_lap else "gangguan_logs"
        data = supabase.table(tbl).select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if data:
            df = pd.DataFrame(data); df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            df_f = df[(pd.to_datetime(df['created_at']).dt.date >= dr[0]) & (pd.to_datetime(df['created_at']).dt.date <= dr[1])]
            st.dataframe(df_f, use_container_width=True)
            p, t = st.selectbox("Diketahui:", list_peg), st.selectbox("Dibuat:", list_tek)
            if st.button("📄 CETAK PDF"):
                b = generate_pdf_final(df_f, f"{dr[0]} - {dr[1]}", staff_map[p], staff_map[t], "LAPORAN", "Maintenance" if "Checklist" in tipe_lap else "Gangguan")
                if b: st.download_button("Download PDF", b, f"Laporan.pdf", "application/pdf")

elif st.session_state.hal == 'Statistik':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    raw_g = supabase.table("gangguan_logs").select("*").execute().data
    if raw_g:
        df_g = pd.DataFrame(raw_g)
        st.plotly_chart(px.pie(df_g, names='status', title="Status Gangguan", hole=0.4))