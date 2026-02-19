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

# --- 2. SOW DATA (Scope of Work) ---
SOW_DATA = {
    "Harian": ["Level Bahan Bakar", "Temperatur Ruangan Server", "Indikator Panel", "Kebersihan Area"],
    "Mingguan": ["Tegangan Battery Start", "Filter Udara AC", "Tekanan Air Plumbing", "Lampu Darurat"],
    "Bulanan": ["Uji Running Genset", "Outdoor AC", "Kekencangan Baut Panel", "Grounding System"]
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

# --- 4. FUNGSI PDF (ANTI-KORUP) ---
def generate_pdf(df, rentang_tgl, peg_data, tek_data, judul="LAPORAN"):
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"{judul} ME - BI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, f"Periode: {rentang_tgl}", ln=True, align="C")
        pdf.ln(10)
        
        # Header Tabel
        pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        w = [55, 25, 35, 35, 127]
        cols = ["Aset", "Kategori", "Teknisi", "Status/Kondisi", "Keterangan/Tindakan"]
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln()

        # Isi Tabel
        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(0, 0, 0)
        for _, row in df.iterrows():
            aset = str(row.get('Nama Aset', '-'))
            kat = str(row.get('periode', row.get('urgensi', '-')))
            tek = str(row.get('teknisi', '-'))
            stts = str(row.get('kondisi', row.get('status', '-')))
            # Jika ada tindakan perbaikan, tampilkan juga
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
        
        # Footer Tanda Tangan (Format Pak Dani)
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

# --- 5. SETUP DATA ---
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

# --- 6. ROUTING HALAMAN ---
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
    df_g = pd.DataFrame(supabase.table("gangguan_logs").select("*").execute().data)
    if not df_g.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Laporan", len(df_g))
        c2.metric("Masih Rusak (Open)", len(df_g[df_g['status'] == 'Open']))
        c3.metric("Sudah OK (Closed)", len(df_g[df_g['status'] == 'Closed']))
        st.plotly_chart(px.pie(df_g, names='status', title="Persentase Penyelesaian", hole=0.4))
    else: st.info("Data belum tersedia.")

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("⚠️ Lapor Gangguan Baru")
    with st.form("f_gangguan"):
        sel_a = st.selectbox("Aset", list(opt_asset.keys()))
        t = st.selectbox("Pelapor", list_tek)
        urg = st.selectbox("Urgensi", ["Sedang", "Mendesak", "Darurat"])
        masalah = st.text_area("Deskripsi Kerusakan")
        foto = st.camera_input("Foto Kerusakan")
        if st.form_submit_button("KIRIM LAPORAN"):
            url = upload_foto(foto)
            supabase.table("gangguan_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "teknisi": t, 
                "masalah": masalah, "urgensi": urg, "status": "Open", "foto_kerusakan_url": url
            }).execute()
            st.success("Terkirim!"); st.rerun()

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("🔄 Update Status Perbaikan")
    data_g = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if data_g:
        for g in data_g:
            with st.expander(f"🔴 {g['assets']['nama_aset']} ({g['urgensi']})"):
                st.write(f"Masalah: {g['masalah']}")
                t_per = st.selectbox("Teknisi Perbaikan", list_tek, key=f"tk_{g['id']}")
                tindakan = st.text_area("Tindakan yang dilakukan", key=f"tnd_{g['id']}")
                foto_after = st.camera_input("Foto Sesudah Perbaikan", key=f"aft_{g['id']}")
                if st.button("Simpan & Tutup Laporan", key=f"btn_{g['id']}"):
                    if tindakan:
                        url_a = upload_foto(foto_after)
                        supabase.table("gangguan_logs").update({
                            "status": "Closed", "tindakan_perbaikan": tindakan, 
                            "teknisi_perbaikan": t_per, "tgl_perbaikan": datetime.datetime.now().isoformat(),
                            "foto_setelah_perbaikan_url": url_a
                        }).eq("id", g['id']).execute()
                        st.success("Status Diperbarui!"); st.rerun()
                    else: st.warning("Isi tindakan perbaikan.")
    else: st.info("Tidak ada laporan kerusakan yang aktif.")

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"📋 Checklist {st.session_state.hal}")
    with st.form("f_chk"):
        sel_a = st.selectbox("Aset", list(opt_asset.keys()))
        t = st.selectbox("Teknisi", list_tek)
        st.write("**Poin Pemeriksaan SOW:**")
        resp = []
        for i, item in enumerate(SOW_DATA[st.session_state.hal]):
            r = st.radio(f"{item}", ["Normal", "Tidak Normal", "N/A"], horizontal=True, key=f"s_{i}")
            resp.append(f"{item}: {r}")
        kon = st.radio("Kondisi Akhir", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
        catatan = st.text_area("Catatan Tambahan")
        if st.form_submit_button("SIMPAN"):
            ket_final = " | ".join(resp) + (f" | Catatan: {catatan}" if catatan else "")
            supabase.table("maintenance_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "teknisi": t, 
                "periode": st.session_state.hal, "kondisi": kon, "keterangan": ket_final
            }).execute()
            st.success("Tersimpan!"); st.rerun()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Export Laporan")
    t1, t2 = st.tabs(["📑 Log Checklist (H/M/B)", "⚠️ Log Kerusakan & Perbaikan"])
    
    with t1:
        res = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if res:
            df1 = pd.DataFrame(res); df1['Nama Aset'] = df1['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            dr1 = st.date_input("Filter Tanggal Checklist", [datetime.date.today(), datetime.date.today()], key="dr1")
            if len(dr1) == 2:
                df1f = df1[(pd.to_datetime(df1['created_at']).dt.date >= dr1[0]) & (pd.to_datetime(df1['created_at']).dt.date <= dr1[1])]
                st.dataframe(df1f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'created_at']], use_container_width=True)
                p, t = st.selectbox("Pilih Pejabat BI", list_peg, key="p1"), st.selectbox("Pilih Teknisi PJ", list_tek, key="t1")
                if st.button("CETAK PDF CHECKLIST"):
                    pb = generate_pdf(df1f, f"{dr1[0]} sd {dr1[1]}", staff_map[p], staff_map[t], "LAPORAN CHECKLIST")
                    if pb: st.download_button("Klik untuk Download", pb, "Checklist.pdf", "application/pdf")
    with t2:
        res2 = supabase.table("gangguan_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if res2:
            df2 = pd.DataFrame(res2); df2['Nama Aset'] = df2['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            dr2 = st.date_input("Filter Tanggal Kerusakan", [datetime.date.today(), datetime.date.today()], key="dr2")
            if len(dr2) == 2:
                df2f = df2[(pd.to_datetime(df2['created_at']).dt.date >= dr2[0]) & (pd.to_datetime(df2['created_at']).dt.date <= dr2[1])]
                st.dataframe(df2f[['Nama Aset', 'urgensi', 'teknisi', 'status', 'tindakan_perbaikan']], use_container_width=True)
                p2, t2 = st.selectbox("Pilih Pejabat BI", list_peg, key="p2"), st.selectbox("Pilih Teknisi PJ", list_tek, key="t2")
                if st.button("CETAK PDF GANGGUAN"):
                    pb2 = generate_pdf(df2f, f"{dr2[0]} sd {dr2[1]}", staff_map[p2], staff_map[t2], "LAPORAN KERUSAKAN")
                    if pb2: st.download_button("Klik untuk Download", pb2, "Laporan_Gangguan.pdf", "application/pdf")