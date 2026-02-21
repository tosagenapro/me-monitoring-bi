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
        "Mingguan": ["Kekencangan baut", "Fung