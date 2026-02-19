import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
from fpdf import FPDF
import json
import plotly.express as px
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
        except Exception as e:
            st.error(f"Gagal upload: {e}")
            return None
    return None

# --- 3. FUNGSI GENERATE PDF (FIXED) ---
def generate_pdf(df, rentang_tgl, peg_data, tek_data):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "LAPORAN PEMELIHARAAN ME - BI BALIKPAPAN", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 7, f"Periode: {rentang_tgl}", ln=True, align="C")
    pdf.ln(10)
    
    # Header Tabel
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(0, 173, 239)
    pdf.set_text_color(255, 255, 255)
    w = [55, 25, 35, 35, 127]
    cols = ["Aset", "Periode", "Teknisi", "Kondisi", "Keterangan"]
    for i in range(len(cols)): pdf.cell(w[i], 10, cols[i], 1, 0, "C", True)
    pdf.ln()

    # Isi Tabel
    pdf.set_font("Helvetica", "", 8); pdf.set_text_color(0, 0, 0)
    for _, row in df.iterrows():
        start_y = pdf.get_y()
        pdf.multi_cell(w[0], 10, str(row['Nama Aset']), 1, 'L')
        y_aset = pdf.get_y()
        pdf.set_xy(10 + w[0] + w[1] + w[2] + w[3], start_y)
        pdf.multi_cell(w[4], 10, str(row['keterangan']), 1, 'L')
        y_detail = pdf.get_y()
        
        max_h = max(y_aset, y_detail) - start_y
        # Menggambar ulang border agar tingginya sama
        pdf.rect(10, start_y, w[0], max_h)
        pdf.rect(10+w[0], start_y, w[1], max_h)
        pdf.rect(10+w[0]+w[1], start_y, w[2], max_h)
        pdf.rect(10+w[0]+w[1]+w[2], start_y, w[3], max_h)
        
        pdf.set_xy(10+w[0], start_y)
        pdf.cell(w[1], max_h, str(row.get('periode', '-')), 0, 0, "C")
        pdf.cell(w[2], max_h, str(row['teknisi']), 0, 0, "C")
        pdf.cell(w[3], max_h, str(row['kondisi']), 0, 0, "C")
        pdf.set_y(start_y + max_h)
        if pdf.get_y() > 170: pdf.add_page()

    # --- TANDA TANGAN (SESUAI FORMAT REQUEST) ---
    pdf.ln(15); cur_y = pdf.get_y(); pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(10, cur_y); pdf.cell(138, 5, "Diketahui,", 0, 0, "C")
    pdf.set_xy(148, cur_y); pdf.cell(138, 5, "Dibuat oleh,", 0, 1, "C")
    
    # Baris Posisi
    pdf.cell(138, 5, str(peg_data.get('posisi', '')), 0, 0, "C")
    pdf.cell(138, 5, "CV. INDO MEGA JAYA", 0, 1, "C")
    
    pdf.ln(18)
    
    # Baris Nama (Underlined)
    pdf.set_font("Helvetica", "BU", 10)
    pdf.cell(138, 5, str(peg_data.get('nama', '')), 0, 0, "C")
    pdf.cell(138, 5, str(tek_data.get('nama', '')), 0, 1, "C")
    
    # Baris Jabatan_pdf
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(138, 5, str(peg_data.get('jabatan_pdf', '')), 0, 0, "C")
    pdf.cell(138, 5, "Teknisi ME", 0, 1, "C")
    
    return pdf.output()

# --- 4. DATA & NAVIGASI ---
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
        if st.button("📊 STATISTIK ASET"): pindah('Statistik'); st.rerun()
    with c2:
        if st.button("⚠️ LAPOR GANGGUAN"): pindah('Gangguan'); st.rerun()
        if st.button("🔄 UPDATE PERBAIKAN"): pindah('Update'); st.rerun()
        if st.button("📑 EXPORT PDF"): pindah('Export'); st.rerun()

elif st.session_state.hal == 'Statistik':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Statistik Kondisi Perangkat")
    logs = supabase.table("maintenance_logs").select("*, assets(nama_aset)").execute().data
    if logs:
        df_s = pd.DataFrame(logs)
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_s, names='kondisi', title="Kondisi Asset", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(df_s, x='periode', color='kondisi', title="Laporan Per Periode")
            st.plotly_chart(fig2, use_container_width=True)

elif st.session_state.hal == 'Gangguan':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("⚠️ Lapor Gangguan / Kerusakan")
    sel_a = st.selectbox("Pilih Aset Bermasalah", list(opt_asset.keys()))
    t = st.selectbox("Pelapor (Teknisi)", list_tek)
    masalah = st.text_area("Deskripsi Kerusakan")
    foto_g = st.camera_input("Ambil Foto Bukti Kerusakan") 
    if st.button("KIRIM LAPORAN"):
        if masalah:
            url_foto = upload_foto(foto_g) if foto_g else None
            supabase.table("gangguan_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "pelapor": t, 
                "masalah": masalah, "status": "Open", "foto_url": url_foto
            }).execute()
            st.error("Laporan Dikirim!"); st.rerun()
        else: st.warning("Isi deskripsi masalah.")

elif st.session_state.hal == 'Update':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("🔄 Update Status Perbaikan")
    data_g = supabase.table("gangguan_logs").select("*, assets(nama_aset)").eq("status", "Open").execute().data
    if data_g:
        for g in data_g:
            with st.expander(f"🔴 {g['assets']['nama_aset']} - {g['created_at'][:10]}"):
                st.write(f"**Masalah:** {g['masalah']}")
                if g.get('foto_url'): st.image(g['foto_url'], width=300)
                foto_fix = st.camera_input(f"Foto Hasil Perbaikan", key=f"cam_{g['id']}")
                if st.button(f"Selesai Diperbaiki", key=f"btn_{g['id']}"):
                    url_foto_fix = upload_foto(foto_fix) if foto_fix else None
                    supabase.table("gangguan_logs").update({
                        "status": "Closed", "foto_perbaikan_url": url_foto_fix
                    }).eq("id", g['id']).execute()
                    st.success("Status Diperbarui!"); st.rerun()
    else: st.info("Tidak ada gangguan aktif.")

elif st.session_state.hal in ['Harian', 'Mingguan', 'Bulanan']:
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader(f"Form {st.session_state.hal}")
    with st.form("f_maintenance", clear_on_submit=True):
        sel_a = st.selectbox("Pilih Aset", list(opt_asset.keys()))
        t = st.selectbox("Teknisi", list_tek)
        kon = st.radio("Kondisi", ["Sangat Baik", "Baik", "Perlu Perbaikan", "Rusak"], index=1)
        ket = st.text_area("Keterangan")
        if st.form_submit_button("💾 SIMPAN DATA"):
            supabase.table("maintenance_logs").insert({
                "asset_id": opt_asset[sel_a]['id'], "teknisi": t, 
                "periode": st.session_state.hal, "kondisi": kon, "keterangan": ket
            }).execute()
            st.success("Data Tersimpan!"); st.balloons()

elif st.session_state.hal == 'Export':
    if st.button("⬅️ KEMBALI"): pindah('Menu'); st.rerun()
    st.subheader("📊 Export PDF")
    logs = supabase.table("maintenance_logs").select("*, assets(nama_aset)").order("created_at", desc=True).execute().data
    if logs:
        df = pd.DataFrame(logs)
        df['Nama Aset'] = df['assets'].apply(lambda x: x['nama_aset'] if x else "N/A")
        df['Tanggal'] = pd.to_datetime(df['created_at']).dt.date
        tgl_r = st.date_input("Rentang Tanggal", [datetime.date.today(), datetime.date.today()])
        
        if len(tgl_r) == 2:
            df_f = df[(df['Tanggal'] >= tgl_r[0]) & (df['Tanggal'] <= tgl_r[1])]
            st.dataframe(df_f[['Nama Aset', 'periode', 'teknisi', 'kondisi', 'Tanggal']], use_container_width=True)
            
            p_sel = st.selectbox("Diketahui (BI)", list_peg)
            t_sel = st.selectbox("Dibuat (Teknisi)", list_tek)
            
            # PROSES DOWNLOAD
            if not df_f.empty:
                pdf_output = generate_pdf(df_f, f"{tgl_r[0]} s/d {tgl_r[1]}", staff_map[p_sel], staff_map[t_sel])
                st.download_button(
                    label="📥 DOWNLOAD PDF",
                    data=pdf_output,
                    file_name=f"Laporan_ME_{tgl_r[0]}_ke_{tgl_r[1]}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("Tidak ada data pada rentang tanggal tersebut.")