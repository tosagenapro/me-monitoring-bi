import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px
import time

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(
    page_title="SIMANTAP ME BI BPP", 
    page_icon="⚡", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. MASTER SOW DINAMIS ---
SOW_MASTER = {
    "AC": {
        "Harian": ["Suhu Ruangan Server (°C)", "Cek suara abnormal outdoor", "Cek kebocoran air indoor"],
        "Mingguan": ["Arus Motor Fan (Ampere)", "Pembersihan filter udara", "Cek kondisi remote"],
        "Bulanan": ["Tekanan Freon (Psi)", "Cuci evaporator", "Cek arus total (Ampere)"]
    },
    "GENSET": {
        "Harian": ["Persentase Bahan Bakar (%)", "Level Oli", "Tegangan Baterai (Volt)"],
        "Mingguan": ["Suhu Mesin saat Running (°C)", "Uji pemanasan (Menit)", "Cek kebocoran"],
        "Bulanan": ["Tegangan Output L-N (Volt)", "Frekuensi (Hz)", "Cek sistem proteksi"]
    },
    "UPS": {
        "Harian": ["Persentase Kapasitas Baterai (%)", "Tegangan Input (Volt)", "Cek Lampu Indikator"],
        "Mingguan": ["Tegangan Output (Volt)", "Suhu Battery Pack (°C)", "Cek Fan Cooling"],
        "Bulanan": ["Uji Discharge (Menit)", "Cek kekencangan terminal", "Laporan Load Sharing"]
    },
    "PANEL": {
        "Harian": ["Cek lampu indikator", "Cek suara dengung panel", "Cek suhu ruangan panel"],
        "Mingguan": ["Cek kekencangan baut terminal", "Cek fungsi MCB", "Pembersihan debu panel"],
        "Bulanan": ["Pengukuran beban (Ampere)", "Cek grounding", "Thermography (Cek panas)"]
    },
    "UMUM": {
        "Harian": ["Cek kebersihan unit", "Cek fungsi operasional"],
        "Mingguan": ["Pemeriksaan fisik"],
        "Bulanan": ["Catatan performa bulanan"]
    }
}

# --- 3. CSS CUSTOM (COMMAND CENTER VIBES) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    
    .stApp { background: #0f172a; }
    
    /* Dashboard Cards */
    .stat-card {
        background: #1e293b; border-radius: 12px; padding: 15px;
        border-bottom: 3px solid #38bdf8; text-align: center;
    }
    
    /* Header */
    .main-header { 
        text-align: center; padding: 20px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
        border-bottom: 3px solid #38bdf8; border-radius: 0 0 20px 20px; margin-bottom: 20px; 
    }
    .main-header h1 { color: #38bdf8; margin: 0; font-size: 1.6rem; font-weight: 800; }
    
    /* Buttons */
    div.stButton > button { 
        width: 100%; height: 60px !important; background: #1e293b !important; 
        border: 1px solid #334155 !important; border-radius: 12px !important; 
        color: #f8fafc !important; font-weight: bold !important;
        transition: all 0.3s ease; margin-bottom: 10px;
    }
    div.stButton > button:hover { border-color: #38bdf8 !important; transform: translateY(-2px); }
    
    /* Form & Input */
    div[data-testid="stForm"] { background: #1e293b; border-radius: 15px; border: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. HEADER ---
st.markdown("""
    <div class="main-header">
        <h1>⚡ SIMANTAP ME | KPwBI BPP</h1>
        <p style="color:#94a3b8; font-size:0.8rem; margin:0;">Command Center & Monitoring Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. FUNGSI ---
@st.cache_data(ttl=30)
def load_data():
    a = supabase.table("assets").select("*").order("nama_aset").execute().data
    s = supabase.table("staff_me").select("*").execute().data
    return a, s

assets_list, staff_list = load_data()
staff_map = {s['nama']: s for s in staff_list}
opt_asset = {f"{a['kode_qr']} - {a['nama_aset']}": a for a in assets_list}
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

def generate_pdf(df, rentang, peg, tek, judul):
    try:
        pdf = FPDF('L', 'mm', 'A4'); pdf.add_page(); pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"{judul} - BI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10); pdf.cell(0, 7, f"Periode: {rentang}", ln=True, align="C"); pdf.ln(10)
        # Header Tabel
        pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        w = [55, 25, 35, 35, 127]
        cols = ["Aset", "Kategori", "Teknisi", "Status", "Keterangan"]
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln(); pdf.set_font("Helvetica", "", 8); pdf.set_text_color(0, 0, 0)
        # Data
        for _, row in df.iterrows():
            pdf.cell(w[0], 10, str(row.get('Nama Aset','-')), 1); pdf.cell(w[1], 10, str(row.get('periode','-')), 1)
            pdf.cell(w[2], 10, str(row.get('teknisi','-')), 1); pdf.cell(w[3], 10, str(row.get('kondisi','-')), 1)
            pdf.cell(w[4], 10, str(row.get('keterangan','-'))[:80], 1); pdf.ln()
        # Signature
        pdf.ln(10); pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, "Diketahui,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
        pdf.cell(138, 5, str(peg.get('posisi', '')), 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C"); pdf.ln(15)
        pdf.set_font("Helvetica", "BU", 10)
        pdf.cell(138, 5, str(peg.get('nama', '')), 0, 0, "C"); pdf.cell(138, 5, str(tek.get('nama', '')), 0, 1, "C")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(138, 5, str(peg.get('jabatan_pdf', '')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# --- 6. LOGIKA HALAMAN ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
def pindah(n): st.session_state.hal = n

# --- MENU UTAMA ---
if st.session_state.hal == 'Menu':
    # 1. Papan Info Digital
    g_open = supabase.table("gangguan_logs").select("id").eq("status", "Open").execute().data
    m_today = supabase.table("maintenance_logs").select("id").filter("created_at", "gte", datetime.date.today().isoformat()).execute().data
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="stat-card"><small>GANGGUAN</small><br><b style="color:#ef4444; font-size:1.5rem;">{len(g_open)}</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card"><small>CEK HARI INI</small><br><b style="color:#22c55e; font-size:1.5rem;">{len(m_today)}</b></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card"><small>SISTEM</small><br><b style="color:#38bdf8; font-size:1.5rem;">OK</b></div>', unsafe_allow_html=True)
    
    st.write("")
    
    # 2. Timeline Aktivitas (Terbaru)
    with st.expander("🕒 AKTIVITAS TERAKHIR TIM"):
        recent = supabase.table("maintenance_logs").select("teknisi, periode, created_at, assets(nama_aset)").order("created_at", desc=True).limit(3).execute().data
        if recent:
            for r in recent:
                tgl = pd.to_datetime(r['created_at']).strftime('%H:%M')
                st.caption(f"📌 **{tgl}** - {r['teknisi']} cek {r['assets']['nama_aset']} ({r['periode']})")
        else: st.caption("Belum ada aktivitas hari ini.")

    # 3. Tombol Navigasi
    st.write("---")
    col_l, col_r = st.columns(2)
    with col_l:
        if st.button("☀️ HARIAN"): pindah('Harian'); st.rerun()
        if st.button("📅 MINGGUAN"): pindah('Mingguan'); st.rerun()
        if st.button("🏆 BULANAN"): pindah('Bulanan'); st.rerun()
    with col_r:
        if st.button("⚠️ GANGGUAN"): pindah('Gangguan'); st.rerun()
        if st.button("🔄 UPDATE"): pindah('Update'); st.rerun()
        if st.button("📑 LAPORAN"): pindah('Export'); st.rerun()
    
    if st.button("📊 STATISTIK KINERJA"): pindah('Statistik'); st.rerun()

# --- HALAMAN STATISTIK ---
elif st.session_state.hal == 'Statistik':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Analisis Data Pemeliharaan")
    df_g = pd.DataFrame(supabase.table("gangguan_logs").select("*").execute().data)
    if not df_g.empty:
        st.plotly_chart(px.pie(df_g, names='status', title="Status Gangguan Fasilitas", hole=0.4, color_discrete_map={'Open':'#ef4444','Closed':'#22c55e'}))
        st.write("---")
        st.write("**Top 5 Aset Bermasalah**")
        df_g_counts = df_g.merge(pd.DataFrame(assets_list), left_on='asset_id', right_on='id')
        st.bar_chart(df_g_counts['nama_aset'].value_counts().head(5))
    else: st.info("Data belum cukup untuk statistik.")

# --- HALAMAN CHECKLIST (HARIAN/MINGGUAN/BULANAN) ---
elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"📋 Checklist {st.session_state.hal}")
    
    # Smart Search Filter
    search = st.text_input("🔍 Cari Nama Aset...", placeholder="Ketik misal: AC, Genset, atau AHU")
    filtered_assets = {k:v for k,v in opt_asset.items() if search.upper() in k.upper()}
    
    sel_a = st.selectbox("Pilih Aset", list(filtered_assets.keys()))
    asset_data = opt_asset[sel_a]
    nama_up = asset_data['nama_aset'].upper()
    
    k_key = "AC" if "AC" in nama_up else "GENSET" if "GENSET" in nama_up else "UPS" if "UPS" in nama_up else "PANEL" if "PANEL" in nama_up else "UMUM"
    
    with st.form("f_chk"):
        tek = st.selectbox("Teknisi", list_tek)
        res_list = []
        for i, task in enumerate(SOW_MASTER[k_key][st.session_state.hal]):
            if any(x in task.upper() for x in ["%", "VOLT", "AMPERE", "PSI", "°C", "HZ", "MENIT"]):
                val = st.number_input(task, step=0.1, key=f"v_{i}")
                res_list.append(f"{task}: {val}")
            else:
                r = st.radio(task, ["Normal", "Abnormal", "N/A"], horizontal=True, key=f"r_{i}")
                res_list.append(f"{task}: {r}")
        
        kondisi = st.select_slider("Kondisi Akhir", options=["Rusak", "Perlu Perbaikan", "Baik", "Sangat Baik"], value="Baik")
        catatan = st.text_area("Catatan Tambahan")
        
        if st.form_submit_button("💾 SIMPAN DATA"):
            ket_final = " | ".join(res_list) + (f" | Catatan: {catatan}" if catatan else "")
            supabase.table("maintenance_logs").insert({
                "asset_id": asset_data['id'], "teknisi": tek, "periode": st.session_state.hal, 
                "kondisi": kondisi, "keterangan": ket_final
            }).execute()
            st.success("Data Berhasil Disimpan!"); time.sleep(1); st.rerun()

# --- HALAMAN GANGGUAN ---
elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    with st.form("f_gangguan"):
        aset = st.selectbox("Aset Bermasalah", list(opt_asset.keys()))
        pelapor = st.selectbox("Teknisi Pelapor", list_tek)
        urgensi = st.select_slider("Tingkat Urgensi", options=["Rendah", "Sedang", "Tinggi", "Darurat"])
        masalah = st.text_area("Deskripsi Kerusakan")
        foto = st.camera_input("Foto Bukti")
        if st.form_submit_button("🚨 KIRIM LAPORAN"):
            u = upload_foto(foto)
            supabase.table("gangguan_logs").insert({
                "asset_id": opt_asset[aset]['id'], "teknisi": pelapor, 
                "masalah": masalah, "urgensi": urgensi, "status": "Open", "foto_kerusakan_url": u
            }).execute()
            st.warning("Laporan Gangguan Terkirim!"); time.sleep(1); st.rerun()

# --- HALAMAN UPDATE PERBAIKAN ---
elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("🔄 Update Status Perbaikan")
    logs = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if logs:
        for l in logs:
            with st.expander(f"⚠️ {l['assets']['nama_aset']} - {l['urgensi']}"):
                st.write(f"Masalah: {l['masalah']}")
                tek_ex = st.selectbox("Teknisi Eksekutor", list_tek, key=f"ex_{l['id']}")
                solusi = st.text_area("Tindakan Perbaikan", key=f"sol_{l['id']}")
                foto_fin = st.camera_input("Foto Hasil", key=f"fin_{l['id']}")
                if st.button("Tandai Selesai", key=f"btn_{l['id']}"):
                    u_f = upload_foto(foto_fin)
                    supabase.table("gangguan_logs").update({
                        "status": "Closed", "tindakan_perbaikan": solusi, "teknisi_perbaikan": tek_ex,
                        "tgl_perbaikan": datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url": u_f
                    }).eq("id", l['id']).execute()
                    st.success("Berhasil diupdate!"); time.sleep(1); st.rerun()
    else: st.info("Tidak ada pending perbaikan.")

# --- HALAMAN EXPORT PDF ---
elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📑 Penarikan Laporan PDF")
    tab1, tab2 = st.tabs(["Log Pemeliharaan", "Log Gangguan"])
    
    with tab1:
        dr = st.date_input("Pilih Rentang Waktu", [datetime.date.today(), datetime.date.today()])
        per = st.selectbox("Filter Periode", ["Semua", "Harian", "Mingguan", "Bulanan"])
        if len(dr) == 2:
            raw = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
            if raw:
                df = pd.DataFrame(raw); df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'])
                df_f = df[(pd.to_datetime(df['created_at']).dt.date >= dr[0]) & (pd.to_datetime(df['created_at']).dt.date <= dr[1])]
                if per != "Semua": df_f = df_f[df_f['periode'] == per]
                st.dataframe(df_f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'created_at']], use_container_width=True)
                if not df_f.empty:
                    p, t = st.selectbox("Diketahui (BI)", list_peg), st.selectbox("Dibuat (IMJ)", list_tek)
                    if st.button("PROSES PDF"):
                        b = generate_pdf(df_f, f"{dr[0]} s/d {dr[1]}", staff_map[p], staff_map[t], f"LAPORAN {per.upper()}")
                        if b: st.download_button("Download PDF", b, f"Lap_{per}_{dr[0]}.pdf")