import os
import gspread
import streamlit as st
import pandas as pd

# --- CONSTANTES GLOBALES ---
SHEET_ID = "17HdWAA_Taphajpj6l1h1zTlgIQrl6VbKIBWPZytlGgg"
MAIN_WORKSHEET_NAME = "Hoja 1"
COL_PUNTAJE = "PUNTAJE TOTAL SMARTFARM"

# --- CONFIGURACIÓN DE PROXY INTELIGENTE ---
IS_CLOUD = os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud" or "STREAMLIT_SERVER_PORT" in os.environ

if not IS_CLOUD:
    PROXY_URL = "http://Sdagatti:Suya$1973@proxy.conci.com.ar:8080"
    os.environ['HTTP_PROXY'] = PROXY_URL
    os.environ['HTTPS_PROXY'] = PROXY_URL
else:
    # En la nube eliminamos cualquier rastro de proxy
    for var in ["HTTP_PROXY", "HTTPS_PROXY"]:
        if var in os.environ: del os.environ[var]

@st.cache_resource(ttl=3600)
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Falta la llave 'gcp_service_account' en los Secrets de la web.")
        st.stop()
    
    creds = dict(st.secrets["gcp_service_account"])
    # Esto arregla el error de 'Incorrect padding' y los saltos de línea
    if "private_key" in creds:
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    
    return gspread.service_account_from_dict(creds)

@st.cache_data(ttl=300)
def load_data(ws_name):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        df = pd.DataFrame(sh.worksheet(ws_name).get_all_records())
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error en {ws_name}: {e}")
        return pd.DataFrame()
