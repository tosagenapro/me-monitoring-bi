import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import uuid

# --- 1. CONFIG & KONEKSI ---
st.set_page_config(page_title="SIMANTAP BI BPP", layout="wide", initial_sidebar_state="collapsed")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. CSS CUSTOM ---
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

# --- FUNGSI UPLOAD FOTO ---
def upload_foto(file):
    if file is not None:
        filename = f"{uuid.uuid4()}.jpg"
        filepath = f"public/{filename}" 
        try:
            supabase.storage.from_("foto_maintenance").upload(filepath, file.getvalue(), {"content-type": "image/jpeg"})
            return f"{URL}/storage/v1/object/public/foto_maintenance/{filepath}"
        except Exception:
            return None
    return None

# --- 3. FUNGSI GENERATE PDF (PERBAIKAN KORUP) ---
def generate_pdf(df, rentang_tgl, peg_data, tek_data):
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "LAPORAN PEMELIHARAAN ME - BI BALIKPAPAN", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, f"Periode: {rentang_tgl}", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(0, 173, 239); pdf.set_text_color(255, 255, 255)
        w = [55, 25, 35, 35, 127]
        cols = ["Aset", "Jenis/Urgensi", "Teknisi", "Kondisi/Status", "Keterangan/Masalah"]
        for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8); pdf.set_text_color(0, 0, 0)
        for _, row in df.iterrows():
            # Pastikan data bukan None untuk mencegah PDF korup
            aset = str(row.get('Nama Aset', '-'))
            per = str(row.get('periode', row.get('urgensi', '-')))
            tek = str(row.get('teknisi', '-'))
            kon = str(row.get('kondisi', row.get('status', '-')))
            ket = str(row.get('keterangan', row.get('masalah', '-')))

            start_y = pdf.get_y()
            pdf.multi_cell(w[0], 10, aset, 1, 'L')
            y_aset = pdf.get_y()
            pdf.set_xy(10 + w[0] + w[1] + w[2] + w[3], start_y)
            pdf.multi_cell(w[4], 10, ket, 1, 'L')
            y_detail = pdf.get_y()
            max_h = max(y_aset, y_detail) - start_y
            
            pdf.rect(10, start_y, w[0], max_h)
            pdf.rect(10+w[0], start_y, w[1], max_h)
            pdf.rect(10+w[0]+w[1], start_y, w[2], max_h)
            pdf.rect(10+w[0]+w[1]+w[2], start_y, w[3], max_h)
            
            pdf.set_xy(10+w[0], start_y)
            pdf.cell(w[1], max_h, per, 0, 0, "C")
            pdf.cell(w[2], max_h, tek, 0, 0, "C")
            pdf.cell(w[3], max_h, kon, 0, 0, "C")
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
    except Exception as e:
        st.error(f"Gagal membuat PDF: {e}")
        return None

# --- 4. DATA NAVIGASI ---
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

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("⚠️ Lapor Gangguan / Kerusakan")
    sel_a = st.selectbox("Pilih Aset", list(opt_asset.keys()))
    t = st.selectbox("Teknisi Pelapor", list_tek)
    urg = st.selectbox("Urgensi", ["Sedang", "Mendesak", "Darurat"])
    masalah = st.text_area("Deskripsi Kerusakan")
    foto_g = st.camera_input("Foto Kerusakan", key="cam_g")
    foto_file = st.file_uploader("Atau Upload", type=['jpg', 'jpeg', 'png'])
    if st.button("KIRIM LAPORAN"):
        if masalah:
            url_foto = upload_foto(foto_g if foto_g else foto_file)
            supabase.table("gangguan_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "teknisi": t, 
                "masalah": masalah, "urgensi": urg, "status": "Open", "foto_kerusakan_url": url_foto
            }).execute()
            st.success("Laporan Terkirim!"); st.rerun()

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("🔄 Update Status Perbaikan")
    data_g = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if data_g:
        for g in data_g:
            with st.expander(f"🔴 {g['assets']['nama_aset']}"):
                st.write(f"Masalah: {g['masalah']}")
                t_perbaikan = st.selectbox("Teknisi Perbaikan", list_tek, key=f"t_{g['id']}")
                tindakan = st.text_input("Tindakan Perbaikan", key=f"ind_{g['id']}")
                if st.button("Update Selesai", key=f"btn_{g['id']}"):
                    supabase.table("gangguan_logs").update({
                        "status": "Closed", "tindakan_perbaikan": tindakan, 
                        "teknisi_perbaikan": t_perbaikan, "tgl_perbaikan": datetime.datetime.now().isoformat()
                    }).eq("id", g['id']).execute()
                    st.success("Selesai!"); st.rerun()
    else: st.info("Tidak ada gangguan aktif.")

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Export Laporan PDF")
    
    tab1, tab2 = st.tabs(["Log Checklist", "Log Gangguan"])
    
    with tab1:
        logs = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if logs:
            df = pd.DataFrame(logs)
            df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            tgl_r = st.date_input("Rentang Tanggal Checklist", [datetime.date.today(), datetime.date.today()], key="tgl_check")
            if len(tgl_r) == 2:
                df_f = df[(pd.to_datetime(df['created_at']).dt.date >= tgl_r[0]) & (pd.to_datetime(df['created_at']).dt.date <= tgl_r[1])]
                st.dataframe(df_f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'created_at']], use_container_width=True)
                p_sel = st.selectbox("Diketahui (BI)", list_peg, key="p1")
                t_sel = st.selectbox("Dibuat (Teknisi)", list_tek, key="t1")
                if st.button("DOWNLOAD PDF CHECKLIST"):
                    pdf_bytes = generate_pdf(df_f, f"{tgl_r[0]} s/d {tgl_r[1]}", staff_map[p_sel], staff_map[t_sel])
                    if pdf_bytes:
                        st.download_button("Klik Disini Untuk Unduh", data=pdf_bytes, file_name="Log_Checklist.pdf", mime="application/pdf")
        else: st.info("Belum ada data checklist.")

    with tab2:
        g_logs = supabase.table("gangguan_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
        if g_logs:
            df_g = pd.DataFrame(g_logs)
            df_g['Nama Aset'] = df_g['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
            tgl_rg = st.date_input("Rentang Tanggal Gangguan", [datetime.date.today(), datetime.date.today()], key="tgl_gang")
            if len(tgl_rg) == 2:
                df_gf = df_g[(pd.to_datetime(df_g['created_at']).dt.date >= tgl_rg[0]) & (pd.to_datetime(df_g['created_at']).dt.date <= tgl_rg[1])]
                st.dataframe(df_gf[['Nama Aset', 'urgensi', 'teknisi', 'status', 'masalah', 'created_at']], use_container_width=True)
                p_sel_g = st.selectbox("Diketahui (BI)", list_peg, key="p2")
                t_sel_g = st.selectbox("Dibuat (Teknisi)", list_tek, key="t2")
                if st.button("DOWNLOAD PDF GANGGUAN"):
                    pdf_bytes_g = generate_pdf(df_gf, f"{tgl_rg[0]} s/d {tgl_rg[1]}", staff_map[p_sel_g], staff_map[t_sel_g])
                    if pdf_bytes_g:
                        st.download_button("Klik Disini Untuk Unduh", data=pdf_bytes_g, file_name="Log_Gangguan.pdf", mime="application/pdf")
        else: st.info("Belum ada data gangguan.")

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"Form {st.session_state.hal}")
    with st.form("f_m"):
        sel_a = st.selectbox("Aset", list(opt_asset.keys()))
        t = st.selectbox("Teknisi", list_tek)
        kon = st.radio("Kondisi", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
        ket = st.text_area("Keterangan")
        if st.form_submit_button("SIMPAN"):
            supabase.table("maintenance_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "teknisi": t, 
                "periode": st.session_state.hal, "kondisi": kon, "keterangan": ket
            }).execute()
            st.success("Tersimpan!"); st.rerun()