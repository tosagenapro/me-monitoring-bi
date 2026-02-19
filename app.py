import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px
import time

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP ME BI BPP", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. MASTER SOW DINAMIS (PINTAR) ---
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

# --- 3. CSS CUSTOM (UI/UX MODERN) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background: #0f172a; }
    .main-header { 
        text-align: center; padding: 25px; background: #1e293b; 
        border: 2px solid #334155; border-radius: 15px; margin-bottom: 30px; 
    }
    .main-header h1 { color: #38bdf8; margin: 0; font-size: 2rem; letter-spacing: 3px; font-weight: 800; }
    .main-header p { color: #94a3b8; margin: 8px 0 0 0; font-size: 0.95rem; font-style: italic; letter-spacing: 1px; }
    
    div.stButton > button { 
        width: 100%; height: 75px !important; background: #1e293b !important; 
        border: 1px solid #334155 !important; border-radius: 12px !important; 
        color: #38bdf8 !important; font-weight: bold !important; font-size: 0.95rem !important;
        margin-bottom: 10px;
    }
    div.stButton > button:hover { border-color: #38bdf8 !important; background: #0f172a !important; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.2); }
    label { color: #38bdf8 !important; font-weight: bold !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e293b; border-radius: 5px; color: white; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. HEADER UTAMA ---
st.markdown("""
    <div class="main-header">
        <h1>⚡ SIMANTAP ME | KPwBI BALIKPAPAN</h1>
        <p>Sistem Informasi Monitoring Aset & Pemeliharaan Terpadu Fasilitas Mechanical Electrical</p>
    </div>
    """, unsafe_allow_html=True)

# --- 5. FUNGSI PENDUKUNG (FOTO & PDF) ---
def upload_foto(file):
    if file is not None:
        filename = f"{uuid.uuid4()}.jpg"
        filepath = f"public/{filename}" 
        try:
            supabase.storage.from_("foto_maintenance").upload(filepath, file.getvalue(), {"content-type": "image/jpeg"})
            return f"{URL}/storage/v1/object/public/foto_maintenance/{filepath}"
        except: return None
    return None

def generate_pdf(df, rentang_tgl, peg_data, tek_data, judul="LAPORAN"):
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"{judul} ME - BI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, f"Periode: {rentang_tgl}", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        w = [55, 25, 35, 35, 127]
        cols = ["Aset", "Kategori", "Teknisi", "Status", "Keterangan"]
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(0, 0, 0)
        for _, row in df.iterrows():
            aset, kat, tek = str(row.get('Nama Aset', '-')), str(row.get('periode', row.get('urgensi', '-'))), str(row.get('teknisi', '-'))
            stts, ket = str(row.get('kondisi', row.get('status', '-'))), str(row.get('keterangan', row.get('tindakan_perbaikan', row.get('masalah', '-'))))
            
            s_y = pdf.get_y()
            pdf.multi_cell(w[0], 10, aset, 1, 'L')
            y_a = pdf.get_y()
            pdf.set_xy(10+w[0]+w[1]+w[2]+w[3], s_y)
            pdf.multi_cell(w[4], 10, ket, 1, 'L')
            y_d = pdf.get_y()
            h = max(y_a, y_d) - s_y
            pdf.rect(10, s_y, w[0], h); pdf.rect(10+w[0], s_y, w[1], h); pdf.rect(10+w[0]+w[1], s_y, w[2], h); pdf.rect(10+w[0]+w[1]+w[2], s_y, w[3], h)
            pdf.set_xy(10+w[0], s_y); pdf.cell(w[1], h, kat, 0, 0, "C"); pdf.cell(w[2], h, tek, 0, 0, "C"); pdf.cell(w[3], h, stts, 0, 0, "C")
            pdf.set_y(s_y + h)
            if pdf.get_y() > 170: pdf.add_page()
        
        pdf.ln(15); pdf.set_font("Helvetica", "", 10)
        pdf.cell(138, 5, "Diketahui,", 0, 0, "C"); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
        pdf.cell(138, 5, str(peg_data.get('posisi', '')), 0, 0, "C"); pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
        pdf.ln(18)
        pdf.set_font("Helvetica", "BU", 10)
        pdf.cell(138, 5, str(peg_data.get('nama', '')), 0, 0, "C"); pdf.cell(138, 5, str(tek_data.get('nama', '')), 0, 1, "C")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(138, 5, str(peg_data.get('jabatan_pdf', '')), 0, 0, "C"); pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# --- 6. SETUP DATA & NAVIGASI ---
if 'hal' not in st.session_state: st.session_state.hal = 'Menu'
def pindah(n): st.session_state.hal = n

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

# --- 7. ROUTING HALAMAN ---
if st.session_state.hal == 'Menu':
    left, center, right = st.columns([0.4, 2, 0.4])
    with center:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("☀️ CHECKLIST HARIAN"): pindah('Harian'); st.rerun()
            if st.button("📅 CHECKLIST MINGGUAN"): pindah('Mingguan'); st.rerun()
            if st.button("🏆 CHECKLIST BULANAN"): pindah('Bulanan'); st.rerun()
            if st.button("📑 EXPORT PDF"): pindah('Export'); st.rerun()
        with col2:
            if st.button("⚠️ LAPOR GANGGUAN"): pindah('Gangguan'); st.rerun()
            if st.button("🔄 UPDATE PERBAIKAN"): pindah('Update'); st.rerun()
            if st.button("📊 STATISTIK"): pindah('Statistik'); st.rerun()
            if st.button("ℹ️ INFO SISTEM"): st.toast("SIMANTAP ME v2.1 Platinum", icon="⚡")
    st.markdown("---")
    st.caption("<center>© 2026 ME Balikpapan - CV. Indo Mega Jaya</center>", unsafe_allow_html=True)

elif st.session_state.hal == 'Statistik':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    df_g = pd.DataFrame(supabase.table("gangguan_logs").select("*").execute().data)
    if not df_g.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Gangguan", len(df_g))
        c2.metric("Pending", len(df_g[df_g['status'] == 'Open']), delta_color="inverse")
        c3.metric("Clear", len(df_g[df_g['status'] == 'Closed']))
        st.plotly_chart(px.pie(df_g, names='status', title="Kondisi Fasilitas ME", hole=0.4, color_discrete_sequence=['#ef4444', '#22c55e']))
    else: st.info("Belum ada data.")

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    with st.form("f_g"):
        sel_a = st.selectbox("Pilih Aset", list(opt_asset.keys()))
        t = st.selectbox("Pelapor", list_tek); urg = st.selectbox("Urgensi", ["Sedang", "Mendesak", "Darurat"])
        mas = st.text_area("Deskripsi Kerusakan"); foto = st.camera_input("Ambil Foto")
        if st.form_submit_button("KIRIM LAPORAN"):
            u = upload_foto(foto)
            supabase.table("gangguan_logs").insert({"asset_id": opt_asset[sel_a]['id'], "teknisi": t, "masalah": mas, "urgensi": urg, "status": "Open", "foto_kerusakan_url": u}).execute()
            st.success("✅ Laporan Berhasil Dikirim!"); st.toast("Masuk database!", icon="⚠️")
            time.sleep(1.5); st.rerun()

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    data_g = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if data_g:
        for g in data_g:
            with st.expander(f"🔴 {g['assets']['nama_aset']}"):
                t_p = st.selectbox("Teknisi Eksekutor", list_tek, key=f"tk_{g['id']}")
                tindakan = st.text_area("Tindakan", key=f"tnd_{g['id']}")
                foto_a = st.camera_input("Foto Sesudah", key=f"aft_{g['id']}")
                if st.button("Update Selesai", key=f"btn_{g['id']}"):
                    u_a = upload_foto(foto_a)
                    supabase.table("gangguan_logs").update({"status": "Closed", "tindakan_perbaikan": tindakan, "teknisi_perbaikan": t_p, "tgl_perbaikan": datetime.datetime.now().isoformat(), "foto_setelah_perbaikan_url": u_a}).eq("id", g['id']).execute()
                    st.success("✅ Selesai!"); st.balloons(); time.sleep(2); st.rerun()
    else: st.info("Semua perangkat aman (No Pending Task).")

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"📋 Smart Checklist {st.session_state.hal}")
    sel_a_l = st.selectbox("Pilih Aset", list(opt_asset.keys()))
    nama_a = opt_asset[sel_a_l]['nama_aset'].upper()
    k_key = "UMUM"
    if "AC" in nama_a: k_key = "AC"
    elif "GENSET" in nama_a: k_key = "GENSET"
    elif "UPS" in nama_a: k_key = "UPS"
    elif "PANEL" in nama_a: k_key = "PANEL"
    
    with st.form("f_chk"):
        t = st.selectbox("Teknisi", list_tek); st.write(f"--- Parameter {k_key} ---")
        resp = []
        for i, task in enumerate(SOW_MASTER[k_key][st.session_state.hal]):
            check_k = ["%", "VOLT", "AMPERE", "PSI", "°C", "HZ", "MENIT", "PERSENTASE", "SUHU"]
            if any(k in task.upper() for k in check_k):
                val = st.number_input(f"{task}", step=0.1, key=f"n_{i}"); resp.append(f"{task}: {val}")
            else:
                r = st.radio(f"{task}", ["Normal", "Tidak Normal", "N/A"], horizontal=True, key=f"r_{i}"); resp.append(f"{task}: {r}")
        kon = st.radio("Kondisi Keseluruhan", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1); cat = st.text_area("Catatan")
        if st.form_submit_button("💾 SIMPAN"):
            k_f = " | ".join(resp) + (f" | Catatan: {cat}" if cat else "")
            supabase.table("maintenance_logs").insert({"asset_id": opt_asset[sel_a_l]['id'], "teknisi": t, "periode": st.session_state.hal, "kondisi": kon, "keterangan": k_f}).execute()
            st.success(f"✅ Data {nama_a} Berhasil Disimpan!"); st.toast("Checklist Terkirim!", icon="💾")
            if st.session_state.hal == 'Bulanan': st.balloons()
            time.sleep(1.5); st.rerun()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    t1, t2 = st.tabs(["📑 Log Checklist ME", "⚠️ Log Gangguan ME"])
    with t1:
        res = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if res:
            df = pd.DataFrame(res); df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            c1, c2 = st.columns(2)
            with c1: dr = st.date_input("Rentang Tanggal", [datetime.date.today(), datetime.date.today()], key="d1")
            with c2: filter_p = st.selectbox("Filter Periode", ["Semua", "Harian", "Mingguan", "Bulanan"], key="f_p")
            if len(dr) == 2:
                dff = df[(pd.to_datetime(df['created_at']).dt.date >= dr[0]) & (pd.to_datetime(df['created_at']).dt.date <= dr[1])]
                if filter_p != "Semua": dff = dff[dff['periode'] == filter_p]
                st.dataframe(dff[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'created_at']], use_container_width=True)
                if not dff.empty:
                    p, t = st.selectbox("Diketahui (BI)", list_peg, key="p1"), st.selectbox("Dibuat (IMJ)", list_tek, key="t1")
                    if st.button("CETAK PDF CHECKLIST"):
                        pb = generate_pdf(dff, f"{dr[0]} sd {dr[1]} ({filter_p})", staff_map[p], staff_map[t], f"LAPORAN CHECKLIST {filter_p.upper()}")
                        if pb: st.download_button(f"Download PDF {filter_p}", pb, f"Checklist_ME_{filter_p}_{dr[0]}.pdf")
    with t2:
        res2 = supabase.table("gangguan_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if res2:
            df2 = pd.DataFrame(res2); df2['Nama Aset'] = df2['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            dr2 = st.date_input("Filter Tanggal", [datetime.date.today(), datetime.date.today()], key="d2")
            if len(dr2) == 2:
                df2f = df2[(pd.to_datetime(df2['created_at']).dt.date >= dr2[0]) & (pd.to_datetime(df2['created_at']).dt.date <= dr2[1])]
                st.dataframe(df2f[['Nama Aset', 'urgensi', 'teknisi', 'status', 'masalah']], use_container_width=True)
                p2, t2 = st.selectbox("Diketahui (BI)", list_peg, key="p2"), st.selectbox("Dibuat (IMJ)", list_tek, key="t2")
                if st.button("CETAK PDF KERUSAKAN"):
                    pb2 = generate_pdf(df2f, f"{dr2[0]} sd {dr2[1]}", staff_map[p2], staff_map[t2], "LAPORAN KERUSAKAN FASILITAS")
                    if pb2: st.download_button("Download PDF Gangguan", pb2, f"Laporan_Kerusakan_ME_{dr2[0]}.pdf")