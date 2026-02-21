import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px
import time
from PIL import Image, ImageDraw
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
    "AC": {"Harian": ["Suhu Ruangan (°C)", "Cek suara abnormal outdoor", "Cek kebocoran air indoor"], "Mingguan": ["Arus Motor Fan (Ampere)", "Pembersihan filter udara", "Cek kondisi remote"], "Bulanan": ["Tekanan Freon (Psi)", "Cuci evaporator", "Cek arus total (Ampere)"]},
    "AHU": {"Harian": ["Cek tekanan udara (Pa)", "Cek suara bearing motor", "Cek kondisi V-Belt"], "Mingguan": ["Pembersihan pre-filter", "Cek drain pan", "Arus motor (Ampere)"], "Bulanan": ["Cek motor damper", "Cleaning coil", "Inspeksi panel kontrol"]},
    "UPS": {"Harian": ["Kapasitas Baterai (%)", "Tegangan Input (Volt)", "Indikator Lampu"], "Mingguan": ["Tegangan Output (Volt)", "Suhu Battery Pack (°C)", "Cek Fan"], "Bulanan": ["Uji Discharge (Menit)", "Kekencangan terminal", "Laporan Load"]},
    "GENSET": {"Harian": ["Bahan Bakar (%)", "Level Oli", "Tegangan Baterai (Volt)"], "Mingguan": ["Suhu saat Running (°C)", "Uji pemanasan (Menit)", "Cek kebocoran"], "Bulanan": ["Tegangan Output (Volt)", "Frekuensi (Hz)", "Cek sistem proteksi"]},
    "PANEL": {"Harian": ["Lampu indikator", "Suara dengung", "Suhu ruangan panel"], "Mingguan": ["Kekencangan baut", "Fungsi MCB", "Pembersihan debu"], "Bulanan": ["Pengukuran beban (Ampere)", "Cek grounding", "Thermography"]},
    "UMUM": {"Harian": ["Kebersihan unit", "Fungsi operasional"], "Mingguan": ["Pemeriksaan fisik"], "Bulanan": ["Catatan performa bulanan"]}
}

# --- 4. CSS CUSTOM ---
st.markdown("""<style>
    .stApp { background: #0f172a; }
    .main-header { text-align: center; padding: 20px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 3px solid #38bdf8; border-radius: 0 0 20px 20px; margin-bottom: 20px; }
    .main-header h1 { color: #38bdf8; margin: 0; font-size: 1.6rem; font-weight: 800; }
    .stat-card { background: #1e293b; border-radius: 12px; padding: 15px; border-bottom: 3px solid #38bdf8; text-align: center; margin-bottom: 10px; }
    div.stButton > button { width: 100%; height: 55px; background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 12px; color: #f8fafc; font-weight: bold; }
    div.stButton > button:hover { border-color: #38bdf8 !important; color: #38bdf8 !important; }
</style>""", unsafe_allow_html=True)

# --- 5. FUNGSI INTI ---
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
        img = Image.open(file).convert('RGB')
        img.thumbnail((800, 800))
        draw = ImageDraw.Draw(img)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text((10, 10), ts, fill="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        fname = f"{uuid.uuid4()}.jpg"
        supabase.storage.from_("foto_maintenance").upload(fname, buf.getvalue(), {"content-type":"image/jpeg"})
        url = supabase.storage.from_("foto_maintenance").get_public_url(fname)
        if isinstance(url, dict): url = url.get('publicURL', '')
        return url.replace("public/public", "public")
    return None

def generate_pdf_final(df, rentang, peg, tek, judul, tipe="Maintenance"):
    try:
        pdf = FPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"{judul} - KPwBI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10); pdf.cell(0, 7, f"Periode: {rentang}", ln=True, align="C"); pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 8); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        w = [60, 25, 30, 25, 130] if tipe == "Maintenance" else [50, 60, 30, 30, 100]
        cols = ["Nama Aset", "Periode", "Teknisi", "Kondisi", "Detail Pekerjaan"] if tipe == "Maintenance" else ["Nama Aset", "Masalah", "Pelapor", "Status", "Tindakan Perbaikan"]
        
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln(); pdf.set_font("Helvetica", "", 7); pdf.set_text_color(0, 0, 0)
        
        for _, r in df.iterrows():
            pdf.cell(w[0], 10, str(r.get('Nama Aset','')), 1)
            if tipe == "Maintenance":
                pdf.cell(w[1], 10, str(r.get('periode','')), 1)
                pdf.cell(w[2], 10, str(r.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(r.get('kondisi','')), 1)
                pdf.cell(w[4], 10, str(r.get('keterangan',''))[:95], 1)
            else:
                pdf.cell(w[1], 10, str(r.get('masalah',''))[:45], 1)
                pdf.cell(w[2], 10, str(r.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(r.get('status','')), 1)
                pdf.cell(w[4], 10, str(r.get('tindakan_perbaikan',''))[:75], 1)
            pdf.ln()

        # SIGNATURE
        pdf.ln(10); pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, "Known,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
        pdf.cell(138, 5, str(peg.get('Position', '')), 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
        pdf.ln(15); pdf.set_font("Helvetica", "BU", 10)
        pdf.cell(138, 5, str(peg.get('nama', '')), 0, 0, "C"); pdf.cell(138, 5, str(tek.get('nama', '')), 0, 1, "C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, str(peg.get('Jabatan_pdf', '')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")

        if tipe != "Maintenance":
            pdf.add_page(); pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 10, "LAMPIRAN DOKUMENTASI", ln=True, align="C"); pdf.ln(5)
            for _, r in df.iterrows():
                f_b, f_a = r.get('foto_kerusakan_url'), r.get('foto_setelah_perbaikan_url')
                if f_b or f_a:
                    pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 7, f"Unit: {r['Nama Aset']}", ln=True)
                    cy = pdf.get_y()
                    for i, furl in enumerate([f_b, f_a]):
                        if furl and str(furl) != "None":
                            try:
                                res = requests.get(furl, timeout=5)
                                if res.status_code == 200:
                                    img_path = f"temp_{i}.jpg"
                                    with open(img_path, "wb") as f: f.write(res.content)
                                    pdf.image(img_path, x=10 + (i*70), y=cy, w=60)
                                    pdf.set_xy(10 + (i*70), cy+42); pdf.cell(60, 5, "Before" if i==0 else "After", 0, 0, "C")
                            except: pass
                    pdf.ln(55)
                    if pdf.get_y() > 200: pdf.add_page()
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e: st.error(f"PDF Error: {e}"); return None

# --- 6. LOGIKA HALAMAN ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'

# DETEKSI QR OTOMATIS
if qr_code_detected and 'qr_handled' not in st.session_state:
    st.session_state.hal = 'LandingQR'; st.session_state.qr_handled = True

st.markdown("""<div class="main-header"><h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1></div>""", unsafe_allow_html=True)

# A. LANDING QR
if st.session_state.hal == 'LandingQR':
    asset_qr = qr_map.get(qr_code_detected)
    if asset_qr:
        st.markdown(f"<div style='text-align:center; background:#1e293b; padding:20px; border-radius:15px; border:2px solid #38bdf8;'><h2>📍 UNIT: {asset_qr['nama_aset']}</h2></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("☀️ HARIAN"): st.session_state.sel_asset_qr = asset_qr; st.session_state.hal = 'Harian'; st.rerun()
            if st.button("📅 MINGGUAN"): st.session_state.sel_asset_qr = asset_qr; st.session_state.hal = 'Mingguan'; st.rerun()
        with c2:
            if st.button("🏆 BULANAN"): st.session_state.sel_asset_qr = asset_qr; st.session_state.hal = 'Bulanan'; st.rerun()
            if st.button("⚠️ GANGGUAN"): st.session_state.sel_asset_qr = asset_qr; st.session_state.hal = 'Gangguan'; st.rerun()
        if st.button("🏠 MENU UTAMA"): st.query_params.clear(); st.session_state.hal = 'Menu'; st.rerun()
    else: st.error("Aset tidak ditemukan."); st.button("Kembali", on_click=lambda: setattr(st.session_state, 'hal', 'Menu'))

# B. MENU UTAMA
elif st.session_state.hal == 'Menu':
    # Stats Ringkas
    g_open = supabase.table("gangguan_logs").select("id").eq("status", "Open").execute().data
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="stat-card"><small>OPEN GANGGUAN</small><br><b style="color:#ef4444; font-size:1.5rem;">{len(g_open)}</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card"><small>TOTAL UNIT</small><br><b style="color:#38bdf8; font-size:1.5rem;">{len(assets_list)}</b></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card"><small>STATUS SISTEM</small><br><b style="color:#22c55e; font-size:1.5rem;">ONLINE</b></div>', unsafe_allow_html=True)
    
    st.write("---")
    cl, cr = st.columns(2)
    with cl:
        if st.button("☀️ HARIAN"): st.session_state.hal = 'Harian'; st.rerun()
        if st.button("📅 MINGGUAN"): st.session_state.hal = 'Mingguan'; st.rerun()
        if st.button("🏆 BULANAN"): st.session_state.hal = 'Bulanan'; st.rerun()
    with cr:
        if st.button("⚠️ GANGGUAN"): st.session_state.hal = 'Gangguan'; st.rerun()
        if st.button("🔄 UPDATE"): st.session_state.hal = 'Update'; st.rerun()
        if st.button("📑 LAPORAN"): st.session_state.hal = 'Export'; st.rerun()
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("📊 STATISTIK"): st.session_state.hal = 'Statistik'; st.rerun()
    with cb2:
        if st.button("🖼️ MASTER QR"): st.session_state.hal = 'MasterQR'; st.rerun()

# C. CHECKLIST & GANGGUAN & UPDATE (Logika sama seperti sebelumnya, dipastikan terpanggil)
elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    st.subheader(f"📋 Checklist {st.session_state.hal}")
    asset_data = st.session_state.get('sel_asset_qr')
    if not asset_data:
        sel = st.selectbox("Pilih Unit:", list(opt_asset.keys()))
        asset_data = opt_asset[sel]
    
    kat = asset_data.get('kategori', 'UMUM').strip().upper()
    sow = SOW_MASTER.get(kat, SOW_MASTER['UMUM'])[st.session_state.hal]
    with st.form("f_chk"):
        tek = st.selectbox("Teknisi", list_tek); res = []
        for t in sow:
            v = st.radio(t, ["Normal", "Abnormal"], horizontal=True); res.append(f"{t}: {v}")
        kon = st.select_slider("Kondisi Umum", ["Rusak", "Baik", "Sangat Baik"], "Baik")
        if st.form_submit_button("SIMPAN"):
            supabase.table("maintenance_logs").insert({"asset_id": asset_data['id'], "teknisi": tek, "periode": st.session_state.hal, "kondisi": kon, "keterangan": " | ".join(res)}).execute()
            st.success("Tersimpan!"); time.sleep(1); st.session_state.pop('sel_asset_qr', None); st.session_state.hal = 'Menu'; st.rerun()
    if st.button("KEMBALI"): st.session_state.pop('sel_asset_qr', None); st.session_state.hal = 'Menu'; st.rerun()

elif st.session_state.hal == 'Gangguan':
    st.subheader("⚠️ Lapor Gangguan")
    asset_data = st.session_state.get('sel_asset_qr')
    if not asset_data:
        sel = st.selectbox("Pilih Unit:", list(opt_asset.keys()))
        asset_data = opt_asset[sel]
    with st.form("f_g"):
        tek = st.selectbox("Pelapor", list_tek); mas = st.text_area("Masalah")
        foto = st.camera_input("Foto")
        if st.form_submit_button("KIRIM"):
            url = upload_foto(foto)
            supabase.table("gangguan_logs").insert({"asset_id": asset_data['id'], "teknisi": tek, "masalah": mas, "status": "Open", "foto_kerusakan_url": url}).execute()
            st.success("Terkirim!"); time.sleep(1); st.session_state.pop('sel_asset_qr', None); st.session_state.hal = 'Menu'; st.rerun()
    if st.button("KEMBALI"): st.session_state.pop('sel_asset_qr', None); st.session_state.hal = 'Menu'; st.rerun()

elif st.session_state.hal == 'Update':
    st.subheader("🔄 Update Perbaikan")
    open_logs = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    for l in open_logs:
        with st.expander(f"⚠️ {l['assets']['nama_aset']} - {l['masalah']}"):
            with st.form(f"up_{l['id']}"):
                sol = st.text_area("Tindakan")
                f_a = st.camera_input("Foto Selesai", key=f"f_{l['id']}")
                if st.form_submit_button("Selesaikan"):
                    url = upload_foto(f_a)
                    supabase.table("gangguan_logs").update({"status": "Closed", "tindakan_perbaikan": sol, "foto_setelah_perbaikan_url": url, "tgl_perbaikan": datetime.datetime.now().isoformat()}).eq("id", l['id']).execute()
                    st.rerun()
    if st.button("KEMBALI"): st.session_state.hal = 'Menu'; st.rerun()

# F. MODUL STATISTIK (KEMBALI HADIR)
elif st.session_state.hal == 'Statistik':
    st.subheader("📊 Statistik ME")
    data_g = supabase.table("gangguan_logs").select("*").execute().data
    if data_g:
        df_g = pd.DataFrame(data_g)
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.pie(df_g, names='status', title="Status Gangguan", hole=0.4))
        with c2: 
            df_g['date'] = pd.to_datetime(df_g['created_at']).dt.date
            st.plotly_chart(px.line(df_g.groupby('date').size().reset_index(name='count'), x='date', y='count', title="Tren Gangguan"))
    else: st.info("Belum ada data statistik.")
    if st.button("KEMBALI"): st.session_state.hal = 'Menu'; st.rerun()

# G. MODUL MASTER QR (KEMBALI HADIR)
elif st.session_state.hal == 'MasterQR':
    st.subheader("🖼️ Master QR Code")
    sel_aset = st.selectbox("Pilih Aset untuk QR:", list(opt_asset.keys()))
    asset_data = opt_asset[sel_aset]
    qr_url = f"{BASE_URL_APP}?unit={asset_data['kode_qr']}"
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr_url}"
    st.image(qr_api, caption=f"QR Code: {asset_data['nama_aset']}")
    st.code(qr_url)
    if st.button("KEMBALI"): st.session_state.hal = 'Menu'; st.rerun()

# H. EXPORT PDF
elif st.session_state.hal == 'Export':
    st.subheader("📑 Cetak Laporan")
    tipe = st.radio("Tipe:", ["Maintenance", "Gangguan"], horizontal=True)
    dr = st.date_input("Rentang Waktu", [datetime.date.today(), datetime.date.today()])
    if len(dr) == 2:
        p = st.selectbox("Diketahui oleh:", list_peg)
        t = st.selectbox("Dibuat oleh:", list_tek)
        if st.button("CETAK PDF"):
            tbl = "maintenance_logs" if tipe == "Maintenance" else "gangguan_logs"
            data = supabase.table(tbl).select("*, assets(nama_aset)").execute().data
            df = pd.DataFrame(data)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'])
            df_f = df[(pd.to_datetime(df['created_at']).dt.date >= dr[0]) & (pd.to_datetime(df['created_at']).dt.date <= dr[1])]
            pdf_bytes = generate_pdf_final(df_f, f"{dr[0]} - {dr[1]}", staff_map[p], staff_map[t], f"LAPORAN {tipe.upper()}")
            if pdf_bytes: st.download_button("Download", pdf_bytes, "Laporan_ME.pdf")
    if st.button("KEMBALI"): st.session_state.hal = 'Menu'; st.rerun()