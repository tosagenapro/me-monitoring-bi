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

# --- 3. MASTER SOW DINAMIS ---
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

# --- 4. CSS CUSTOM ---
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
        width: 100%; height: 60px !important; background: #1e293b !important; border: 1px solid #334155 !important; 
        border-radius: 12px !important; color: #f8fafc !important; font-weight: bold !important; transition: 0.3s;
    }
    div.stButton > button:hover { border-color: #38bdf8 !important; color: #38bdf8 !important; transform: translateY(-3px); }
    .qr-landing { background: #1e293b; padding: 25px; border-radius: 20px; border: 2px solid #38bdf8; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNGSI INTI ---
@st.cache_data(ttl=30)
def load_data():
    a = supabase.table("assets").select("*").order("nama_aset").limit(200).execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
staff_map = {s['nama']: s for s in staff_list}
opt_asset = {f"[{a['kode_qr']}] {a['nama_aset']}": a for a in assets_list}
qr_map = {a['kode_qr']: a for a in assets_list}

list_tek = [s['nama'] for s in staff_list if s['kategori'] == 'TEKNISI']
list_peg = [s['nama'] for s in staff_list if s['kategori'] == 'PEGAWAI']
list_kat_master = ["SEMUA", "AC", "AHU", "UPS", "BAS", "PANEL", "GENSET", "UMUM"]

def add_timestamp(image_file):
    img = Image.open(image_file)
    if img.mode != 'RGB': img = img.convert('RGB')
    max_w = 800
    w_per = (max_w / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_per)))
    img = img.resize((max_w, h_size), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)
    text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    w, h = img.size
    draw.rectangle([w-170, h-30, w-10, h-10], fill="black")
    draw.text((w-160, h-25), text, fill="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75, optimize=True)
    return buf.getvalue()

def upload_foto(file):
    if file:
        proc_img = add_timestamp(file)
        fname = f"{uuid.uuid4()}.jpg"
        try:
            supabase.storage.from_("foto_maintenance").upload(fname, proc_img, {"content-type":"image/jpeg"})
            res = supabase.storage.from_("foto_maintenance").get_public_url(fname)
            url = res if isinstance(res, str) else res.get('publicURL', res)
            
            # Anti-double public cleaner
            if "public/public" in url:
                url = url.replace("public/public", "public")
                
            return f"{url}?t={int(time.time())}"
        except Exception as e:
            st.error(f"Gagal Upload: {e}"); return None
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
            w = [50, 60, 30, 30, 100]; cols = ["Nama Aset", "Masalah", "Pelapor", "Status", "Tindakan Perbaikan"]
        
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln(); pdf.set_font("Helvetica", "", 7); pdf.set_text_color(0, 0, 0)
        
        for _, r in df.iterrows():
            if tipe == "Maintenance":
                pdf.cell(w[0], 10, str(r.get('Nama Aset','')), 1)
                pdf.cell(w[1], 10, str(r.get('periode','')), 1)
                pdf.cell(w[2], 10, str(r.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(r.get('kondisi','')), 1)
                pdf.cell(w[4], 10, str(r.get('keterangan',''))[:95], 1)
            else:
                pdf.cell(w[0], 10, str(r.get('Nama Aset','')), 1)
                pdf.cell(w[1], 10, str(r.get('masalah',''))[:45], 1)
                pdf.cell(w[2], 10, str(r.get('teknisi','')), 1)
                pdf.cell(w[3], 10, str(r.get('status','')), 1)
                pdf.cell(w[4], 10, str(r.get('tindakan_perbaikan',''))[:75], 1)
            pdf.ln()

        # --- SIGNATURE SECTION (Sesuai Permintaan Pak Dani) ---
        pdf.ln(10); pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, "Known,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
        
        posisi_peg = str(peg.get('Position', '')).replace('"', '')
        pdf.cell(138, 5, posisi_peg, 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
        pdf.ln(20)
        
        # Nama Underlined (BU)
        pdf.set_font("Helvetica", "BU", 10)
        pdf.cell(138, 5, str(peg.get('nama', '')), 0, 0, "C"); pdf.cell(138, 5, str(tek.get('nama', '')), 0, 1, "C")
        
        # Jabatan_pdf
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, str(peg.get('Jabatan_pdf', '')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")

        # --- LAMPIRAN FOTO ---
        if tipe != "Maintenance":
            pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "LAMPIRAN DOKUMENTASI PERBAIKAN", ln=True, align="C"); pdf.ln(5)
            headers = {"User-Agent": "Mozilla/5.0"}
            
            for _, r in df.iterrows():
                f_b, f_a = r.get('foto_kerusakan_url'), r.get('foto_setelah_perbaikan_url')
                if (f_b and str(f_b) != "None") or (f_a and str(f_a) != "None"):
                    pdf.set_font("Helvetica", "B", 9); pdf.cell(0, 7, f"Unit: {r['Nama Aset']}", ln=True)
                    cy = pdf.get_y()
                    
                    def download_img(url_raw):
                        if not url_raw or str(url_raw) == "None": return None
                        url = str(url_raw).strip()
                        if "public/public" in url: url = url.replace("public/public", "public")
                        try:
                            res = requests.get(url, headers=headers, timeout=15)
                            return io.BytesIO(res.content) if res.status_code == 200 else None
                        except: return None

                    img_b = download_img(f_b)
                    if img_b:
                        pdf.image(img_b, x=10, y=cy, w=60)
                        pdf.set_xy(10, cy+42); pdf.cell(60, 5, "Before", 0, 0, "C")
                    elif f_b and str(f_b) != "None":
                        pdf.set_xy(10, cy+15); pdf.cell(60, 5, "[Foto Error]", 0, 0, "C")

                    img_a = download_img(f_a)
                    if img_a:
                        pdf.image(img_a, x=80, y=cy, w=60)
                        pdf.set_xy(80, cy+42); pdf.cell(60, 5, "After", 0, 0, "C")
                    elif f_a and str(f_a) != "None":
                        pdf.set_xy(80, cy+15); pdf.cell(60, 5, "[Foto Error]", 0, 0, "C")
                    
                    pdf.ln(55)
                    if pdf.get_y() > 180: pdf.add_page()
                    
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Gagal PDF: {e}"); return None

# --- 6. ROUTING ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
if qr_code_detected and 'qr_handled' not in st.session_state:
    st.session_state.hal = 'LandingQR'; st.session_state.qr_handled = True

def pindah(n): st.session_state.hal = n

st.markdown("""<div class="main-header"><h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1></div>""", unsafe_allow_html=True)

# --- 7. HALAMAN (LOGIC LANJUTAN) ---

# A. LANDING QR
if st.session_state.hal == 'LandingQR':
    asset_qr = qr_map.get(qr_code_detected)
    if asset_qr:
        st.markdown(f'<div class="qr-landing"><h2>📍 UNIT TERDETEKSI</h2><h3>{asset_qr["nama_aset"]}</h3><p>{asset_qr["kode_qr"]} | {asset_qr["kategori"]}</p></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("☀️ HARIAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Harian'); st.rerun()
            if st.button("📅 MINGGUAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Mingguan'); st.rerun()
        with c2:
            if st.button("🏆 BULANAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Bulanan'); st.rerun()
            if st.button("⚠️ GANGGUAN"): st.session_state.sel_asset_qr = asset_qr; pindah('Gangguan'); st.rerun()
        if st.button("🏠 MENU UTAMA"): st.query_params.clear(); pindah('Menu'); st.rerun()
    else: st.error("QR Code Error."); st.button("Kembali", on_click=lambda: pindah('Menu'))

# B. MENU UTAMA
elif st.session_state.hal == 'Menu':
    g_open = supabase.table("gangguan_logs").select("id").eq("status", "Open").execute().data
    m_today = supabase.table("maintenance_logs").select("id").filter("created_at", "gte", datetime.date.today().isoformat()).execute().data
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="stat-card"><small>GANGGUAN</small><br><b style="color:#ef4444; font-size:1.5rem;">{len(g_open)}</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card"><small>CEK HARI INI</small><br><b style="color:#22c55e; font-size:1.5rem;">{len(m_today)}</b></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card"><small>TOTAL ASET</small><br><b style="color:#38bdf8; font-size:1.5rem;">{len(assets_list)}</b></div>', unsafe_allow_html=True)
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
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("📊 STATISTIK"): pindah('Statistik'); st.rerun()
    with cb2:
        if st.button("🖼️ MASTER QR"): pindah('MasterQR'); st.rerun()

# C. CHECKLIST
elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    st.subheader(f"📋 Checklist {st.session_state.hal}")
    is_qr = 'sel_asset_qr' in st.session_state
    if is_qr:
        asset_data = st.session_state.sel_asset_qr
        st.success(f"Aset: **{asset_data['nama_aset']}**")
    else:
        kat_f = st.radio("Kategori:", list_kat_master, horizontal=True)
        list_p = list(opt_asset.keys()) if kat_f == "SEMUA" else [k for k, v in opt_asset.items() if str(v.get('kategori')).strip().upper() == kat_f.upper()]
        asset_data = opt_asset[st.selectbox("Pilih Unit:", list_p)]

    k_key = str(asset_data.get('kategori')).strip().upper() if str(asset_data.get('kategori')).strip().upper() in SOW_MASTER else "UMUM"
    with st.form("f_chk"):
        tek = st.selectbox("Teknisi", list_tek); res_list = []
        for i, task in enumerate(SOW_MASTER[k_key][st.session_state.hal]):
            if any(x in task.upper() for x in ["%", "VOLT", "AMPERE", "PSI", "°C", "HZ", "PA"]):
                val = st.number_input(task, step=0.1, key=f"v_{i}"); res_list.append(f"{task}: {val}")
            else:
                r = st.radio(task, ["Normal", "Abnormal", "N/A"], horizontal=True, key=f"r_{i}"); res_list.append(f"{task}: {r}")
        kon = st.select_slider("Kondisi", ["Rusak", "Perlu Perbaikan", "Baik", "Sangat Baik"], "Baik"); cat = st.text_area("Catatan")
        if st.form_submit_button("💾 SIMPAN"):
            ket_f = " | ".join(res_list) + (f" | Catatan: {cat}" if cat else "")
            supabase.table("maintenance_logs").insert({"asset_id": asset_data['id'], "teknisi": tek, "periode": st.session_state.hal, "kondisi": kon, "keterangan": ket_f}).execute()
            st.success("Tersimpan!"); time.sleep(1)
            if is_qr: del st.session_state.sel_asset_qr
            pindah('Menu'); st.rerun()
    if st.button("⬅️ BATAL"): 
        if is_qr: del st.session_state.sel_asset_qr
        pindah('Menu'); st.rerun()

# D. GANGGUAN
elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    is_qr = 'sel_asset_qr' in st.session_state
    if is_qr: asset_data = st.session_state.sel_asset_qr
    else:
        kat_g = st.radio("Filter:", list_kat_master, horizontal=True)
        lp = list(opt_asset.keys()) if kat_g=="SEMUA" else [k for k,v in opt_asset.items() if str(v.get('kategori')).strip().upper()==kat_g.upper()]
        asset_data = opt_asset[st.selectbox("Pilih Aset", lp)]

    with st.form("f_g"):
        pel = st.selectbox("Pelapor", list_tek); urg = st.select_slider("Urgensi", ["Rendah", "Sedang", "Tinggi", "Darurat"])
        mas = st.text_area("Masalah"); foto = st.camera_input("Foto Bukti (Timestamp)")
        if st.form_submit_button("🚨 KIRIM"):
            u = upload_foto(foto)
            supabase.table("gangguan_logs").insert({"asset_id": asset_data['id'], "teknisi": pel, "masalah": mas, "urgensi": urg, "status": "Open", "foto_kerusakan_url": u}).execute()
            st.warning("Terkirim!"); time.sleep(1)
            if is_qr: del st.session_state.sel_asset_qr
            pindah('Menu'); st.rerun()

# E. UPDATE (PERBAIKAN)
elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    logs = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if logs:
        for l in logs:
            with st.expander(f"⚠️ {l['assets']['nama_aset']}"):
                with st.form(f"f_up_{l['id']}"):
                    sol = st.text_area("Tindakan"); t_pb = st.selectbox("Teknisi", list_tek); f_up = st.camera_input("Foto Selesai (Timestamp)")
                    if st.form_submit_button("Selesai"):
                        u_f = upload_foto(f_up)
                        supabase.table("gangguan_logs").update({"status":"Closed", "tindakan_perbaikan":sol, "teknisi_perbaikan":t_pb, "tgl_perbaikan":datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url":u_f}).eq("id", l['id']).execute()
                        st.success("Berhasil!"); time.sleep(1); st.rerun()
    else: st.info("Tidak ada perbaikan tertunda.")

# F. MASTER QR
elif st.session_state.hal == 'MasterQR':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    sel_aset_name = st.selectbox("Pilih Aset untuk QR:", list(opt_asset.keys()))
    asset_data = opt_asset[sel_aset_name]
    full_url = f"{BASE_URL_APP}?unit={asset_data['kode_qr']}"
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={full_url}"
    c1, c2 = st.columns([1, 2])
    with c1: st.image(qr_api, caption=f"QR: {asset_data['kode_qr']}")
    with c2: st.success(f"**Aset:** {asset_data['nama_aset']}"); st.code(full_url)

# G. EXPORT
elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📑 Ekspor PDF")
    tipe_lap = st.segmented_control("Tipe:", ["Checklist Maintenance", "Log Gangguan & Perbaikan"], default="Checklist Maintenance")
    dr = st.date_input("Rentang", [datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()])
    p_filter = st.selectbox("Periode:", ["SEMUA", "Harian", "Mingguan", "Bulanan"]) if tipe_lap == "Checklist Maintenance" else "SEMUA"

    if len(dr) == 2:
        tbl = "maintenance_logs" if tipe_lap == "Checklist Maintenance" else "gangguan_logs"
        data = supabase.table(tbl).select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if data:
            df = pd.DataFrame(data); df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            df_f = df[(pd.to_datetime(df['created_at']).dt.date >= dr[0]) & (pd.to_datetime(df['created_at']).dt.date <= dr[1])]
            if tipe_lap == "Checklist Maintenance" and p_filter != "SEMUA": df_f = df_f[df_f['periode'] == p_filter]
            
            st.dataframe(df_f, use_container_width=True)
            if not df_f.empty:
                p, t = st.selectbox("Diketahui:", list_peg), st.selectbox("Dibuat:", list_tek)
                if st.button("📄 CETAK PDF"):
                    with st.spinner("Memproses Laporan & Gambar..."):
                        b = generate_pdf_final(df_f, f"{dr[0]} - {dr[1]}", staff_map[p], staff_map[t], "LAPORAN", "Maintenance" if tipe_lap=="Checklist Maintenance" else "Gangguan")
                        if b: st.download_button("Download PDF", b, f"Laporan_{dr[0]}.pdf")
        else: st.info("Tidak ada data.")

# H. STATISTIK
elif st.session_state.hal == 'Statistik':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    raw_g = supabase.table("gangguan_logs").select("*").execute().data
    if raw_g:
        df_g = pd.DataFrame(raw_g)
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.pie(df_g, names='status', title="Status Gangguan", hole=0.4))
        with c2: st.plotly_chart(px.bar(df_g, x='urgensi', title="Tingkat Urgensi", color='urgensi'))
        st.plotly_chart(px.line(df_g.groupby(pd.to_datetime(df_g['created_at']).dt.date).size().reset_index(name='count'), x='created_at', y='count', title="Tren Gangguan Harian"))
    else: st.info("Data statistik belum tersedia.")