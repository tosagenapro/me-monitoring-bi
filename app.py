import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid
import plotly.express as px

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP BI BPP", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. MASTER SOW BERDASARKAN JENIS ALAT ---
SOW_MASTER = {
    "AC": {
        "Harian": ["Cek temperatur ruangan", "Cek suara abnormal outdoor", "Cek kebocoran air indoor"],
        "Mingguan": ["Pembersihan filter udara", "Cek drainase pembuangan", "Cek kondisi remote"],
        "Bulanan": ["Cuci evaporator", "Cek tekanan freon", "Cek arus motor fan"]
    },
    "GENSET": {
        "Harian": ["Cek level bahan bakar", "Cek level oli", "Cek tegangan baterai (accu)"],
        "Mingguan": ["Uji pemanasan (Warming up)", "Cek kebocoran oli/air", "Cek kebersihan radiator"],
        "Bulanan": ["Uji running beban", "Pembersihan panel kontrol", "Cek sistem proteksi"]
    },
    "PANEL": {
        "Harian": ["Cek lampu indikator", "Cek suara dengung panel", "Cek suhu ruangan panel"],
        "Mingguan": ["Cek kekencangan baut terminal", "Cek fungsi MCB", "Pembersihan debu panel"],
        "Bulanan": ["Pengukuran beban (Ampere)", "Cek grounding", "Thermography (Cek panas)"]
    },
    "UMUM": {
        "Harian": ["Cek kebersihan unit", "Cek fungsi operasional"],
        "Mingguan": ["Pemeriksaan fisik menyeluruh"],
        "Bulanan": ["Laporan performa bulanan"]
    }
}

# --- 3. CSS CUSTOM ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background: #0f172a; }
    .main-header { 
        text-align: center; padding: 15px; background: #1e293b; 
        border: 1px solid #334155; border-radius: 10px; margin-bottom: 25px; 
    }
    .main-header h1 { color: #94a3b8; margin: 0; font-size: 1.4rem; letter-spacing: 2px; }
    div.stButton > button { 
        width: 100%; height: 70px !important; background: #1e293b !important; 
        border: 1px solid #334155 !important; border-radius: 8px !important; 
        color: #38bdf8 !important; font-weight: bold !important; font-size: 0.9rem !important;
    }
    div.stButton > button:hover { border-color: #38bdf8 !important; background: #0f172a !important; }
    label { color: #38bdf8 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI UPLOAD ---
def upload_foto(file):
    if file is not None:
        filename = f"{uuid.uuid4()}.jpg"
        filepath = f"public/{filename}" 
        try:
            supabase.storage.from_("foto_maintenance").upload(filepath, file.getvalue(), {"content-type": "image/jpeg"})
            return f"{URL}/storage/v1/object/public/foto_maintenance/{filepath}"
        except: return None
    return None

# --- FUNGSI PDF (STABIL) ---
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
            aset = str(row.get('Nama Aset', '-'))
            kat = str(row.get('periode', row.get('urgensi', '-')))
            tek = str(row.get('teknisi', '-'))
            stts = str(row.get('kondisi', row.get('status', '-')))
            ket = str(row.get('keterangan', row.get('tindakan_perbaikan', row.get('masalah', '-'))))
            
            start_y = pdf.get_y()
            pdf.multi_cell(w[0], 10, aset, 1, 'L')
            y_aset = pdf.get_y()
            pdf.set_xy(10 + w[0] + w[1] + w[2] + w[3], start_y)
            pdf.multi_cell(w[4], 10, ket, 1, 'L')
            y_detail = pdf.get_y()
            max_h = max(y_aset, y_detail) - start_y
            
            pdf.rect(10, start_y, w[0], max_h); pdf.rect(10+w[0], start_y, w[1], max_h)
            pdf.rect(10+w[0]+w[1], start_y, w[2], max_h); pdf.rect(10+w[0]+w[1]+w[2], start_y, w[3], max_h)
            pdf.set_xy(10+w[0], start_y)
            pdf.cell(w[1], max_h, kat, 0, 0, "C")
            pdf.cell(w[2], max_h, tek, 0, 0, "C")
            pdf.cell(w[3], max_h, stts, 0, 0, "C")
            pdf.set_y(start_y + max_h)
            if pdf.get_y() > 170: pdf.add_page()
        
        # FOOTER TANDA TANGAN (Format Pak Dani)
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

# --- 4. SETUP DATA ---
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

st.markdown('<div class="main-header"><h1>⚡ SIMANTAP BI BALIKPAPAN</h1></div>', unsafe_allow_html=True)

# --- 5. ROUTING HALAMAN ---
if st.session_state.hal == 'Menu':
    c1, mid, c2 = st.columns([1, 0.2, 1])
    with c1:
        if st.button("☀️ CHECKLIST HARIAN"): pindah('Harian'); st.rerun()
        if st.button("📅 CHECKLIST MINGGUAN"): pindah('Mingguan'); st.rerun()
        if st.button("🏆 CHECKLIST BULANAN"): pindah('Bulanan'); st.rerun()
        if st.button("📑 EXPORT PDF"): pindah('Export'); st.rerun()
    with c2:
        if st.button("⚠️ LAPOR GANGGUAN"): pindah('Gangguan'); st.rerun()
        if st.button("🔄 UPDATE PERBAIKAN"): pindah('Update'); st.rerun()
        if st.button("📊 STATISTIK"): pindah('Statistik'); st.rerun()

elif st.session_state.hal == 'Statistik':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Dashboard Kondisi Perangkat")
    df_g = pd.DataFrame(supabase.table("gangguan_logs").select("*").execute().data)
    if not df_g.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Gangguan", len(df_g))
        c2.metric("Perlu Perbaikan (Open)", len(df_g[df_g['status'] == 'Open']), delta_color="inverse")
        c3.metric("Berhasil Diperbaiki", len(df_g[df_g['status'] == 'Closed']))
        st.plotly_chart(px.pie(df_g, names='status', title="Status Perangkat Saat Ini", hole=0.4, color_discrete_sequence=['#ef4444', '#22c55e']))
    else: st.info("Data belum tersedia.")

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("⚠️ Form Laporan Kerusakan")
    with st.form("f_gangguan"):
        sel_a = st.selectbox("Pilih Aset", list(opt_asset.keys()))
        t = st.selectbox("Teknisi Pelapor", list_tek)
        urg = st.selectbox("Urgensi", ["Sedang", "Mendesak", "Darurat"])
        masalah = st.text_area("Deskripsi Kerusakan")
        foto = st.camera_input("Ambil Foto Kerusakan") # FITUR FOTO TETAP ADA
        if st.form_submit_button("KIRIM LAPORAN"):
            url = upload_foto(foto)
            supabase.table("gangguan_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "teknisi": t, "masalah": masalah, 
                "urgensi": urg, "status": "Open", "foto_kerusakan_url": url
            }).execute()
            st.success("Laporan Berhasil Dikirim!"); st.rerun()

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("🔄 Update Hasil Perbaikan")
    data_g = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if data_g:
        for g in data_g:
            with st.expander(f"🔴 {g['assets']['nama_aset']} ({g['urgensi']})"):
                st.write(f"Masalah: {g['masalah']}")
                t_p = st.selectbox("Teknisi Eksekutor", list_tek, key=f"tk_{g['id']}")
                tindakan = st.text_area("Tindakan Perbaikan", key=f"tnd_{g['id']}")
                foto_aft = st.camera_input("Foto Setelah Perbaikan", key=f"aft_{g['id']}") # FITUR FOTO PERBAIKAN
                if st.button("Simpan & Selesai", key=f"btn_{g['id']}"):
                    url_a = upload_foto(foto_aft)
                    supabase.table("gangguan_logs").update({
                        "status": "Closed", "tindakan_perbaikan": tindakan, 
                        "teknisi_perbaikan": t_p, "tgl_perbaikan": datetime.datetime.now().isoformat(),
                        "foto_setelah_perbaikan_url": url_a
                    }).eq("id", g['id']).execute()
                    st.success("Laporan Ditutup!"); st.rerun()
    else: st.info("Tidak ada pekerjaan perbaikan.")

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"📋 Checklist {st.session_state.hal}")
    sel_a_label = st.selectbox("Pilih Aset", list(opt_asset.keys()))
    nama_aset = opt_asset[sel_a_label]['nama_aset'].upper()
    
    # DETEKSI SMART SOW
    k_key = "UMUM"
    if "AC" in nama_aset: k_key = "AC"
    elif "GENSET" in nama_aset: k_key = "GENSET"
    elif "PANEL" in nama_aset: k_key = "PANEL"

    with st.form("f_chk"):
        t = st.selectbox("Teknisi", list_tek)
        st.write(f"--- Poin Pemeriksaan {k_key} ---")
        resp = []
        for i, task in enumerate(SOW_MASTER[k_key][st.session_state.hal]):
            r = st.radio(f"{task}", ["Normal", "Tidak Normal", "N/A"], horizontal=True, key=f"tsk_{i}")
            resp.append(f"{task}: {r}")
        kon = st.radio("Kondisi Keseluruhan", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
        cat = st.text_area("Catatan")
        if st.form_submit_button("SIMPAN"):
            k_final = " | ".join(resp) + (f" | Catatan: {cat}" if cat else "")
            supabase.table("maintenance_logs").insert({
                "asset_id": opt_asset[sel_a_label]['id'], "teknisi": t, 
                "periode": st.session_state.hal, "kondisi": kon, "keterangan": k_final
            }).execute()
            st.success("Checklist Tersimpan!"); st.rerun()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Export PDF")
    t1, t2 = st.tabs(["📑 Log Checklist", "⚠️ Log Gangguan"])
    with t1:
        res = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if res:
            df = pd.DataFrame(res); df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            dr = st.date_input("Rentang Tanggal", [datetime.date.today(), datetime.date.today()], key="d1")
            if len(dr) == 2:
                dff = df[(pd.to_datetime(df['created_at']).dt.date >= dr[0]) & (pd.to_datetime(df['created_at']).dt.date <= dr[1])]
                st.dataframe(dff[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'created_at']], use_container_width=True)
                p, t = st.selectbox("Diketahui", list_peg, key="p1"), st.selectbox("Dibuat", list_tek, key="t1")
                if st.button("CETAK PDF CHECKLIST"):
                    pb = generate_pdf(dff, f"{dr[0]} sd {dr[1]}", staff_map[p], staff_map[t], "LAPORAN CHECKLIST")
                    if pb: st.download_button("Download", pb, "Checklist.pdf")
    with t2:
        res2 = supabase.table("gangguan_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if res2:
            df2 = pd.DataFrame(res2); df2['Nama Aset'] = df2['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            dr2 = st.date_input("Rentang Tanggal", [datetime.date.today(), datetime.date.today()], key="d2")
            if len(dr2) == 2:
                df2f = df2[(pd.to_datetime(df2['created_at']).dt.date >= dr2[0]) & (pd.to_datetime(df2['created_at']).dt.date <= dr2[1])]
                st.dataframe(df2f[['Nama Aset', 'urgensi', 'teknisi', 'status', 'masalah']], use_container_width=True)
                p2, t2 = st.selectbox("Diketahui", list_peg, key="p2"), st.selectbox("Dibuat", list_tek, key="t2")
                if st.button("CETAK PDF KERUSAKAN"):
                    pb2 = generate_pdf(df2f, f"{dr2[0]} sd {dr2[1]}", staff_map[p2], staff_map[t2], "LAPORAN KERUSAKAN")
                    if pb2: st.download_button("Download", pb2, "Gangguan.pdf")