# conexion.py
import os
import gspread
import streamlit as st
import pandas as pd

# --- CONSTANTES GLOBALES ---
SHEET_ID = "17HdWAA_Taphajpj6l1h1zTlgIQrl6VbKIBWPZytlGgg"
MAIN_WORKSHEET_NAME = "Hoja 1"
COL_PUNTAJE = "PUNTAJE TOTAL SMARTFARM"

# --- CONFIGURACIÓN DE PROXY BLINDADA ---
# Detectamos si estamos en la nube o en la oficina (Conci)
IS_CLOUD = os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud" or "STREAMLIT_SERVER_PORT" in os.environ

if not IS_CLOUD:
    # Entorno Local Conci
    PROXY_URL = "http://Sdagatti:Suya$1973@proxy.conci.com.ar:8080"
    os.environ['HTTP_PROXY'] = PROXY_URL
    os.environ['HTTPS_PROXY'] = PROXY_URL
else:
    # Entorno Nube Streamlit (Limpiamos proxy para evitar errores)
    if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
    if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]
    os.environ['no_proxy'] = '*'

# --- FUNCIONES DE CONEXIÓN ---

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Conecta usando los Secrets configurados en Streamlit Cloud"""
    # Esta línea busca el [gcp_service_account] que pegaste en los Secrets de la web
    creds_dict = st.secrets["gcp_service_account"]
    return gspread.service_account_from_dict(creds_dict)

@st.cache_data(ttl=300)
def load_data(ws_name):
    """Carga datos de una pestaña específica"""
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        df = pd.DataFrame(sh.worksheet(ws_name).get_all_records())
        # Normalizamos nombres de columnas
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        # Esto te dirá el error exacto en la pantalla de Streamlit si algo falla
        st.error(f"Error al cargar {ws_name}: {e}")
        return pd.DataFrame()