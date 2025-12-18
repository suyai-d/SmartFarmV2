import os
import gspread
import streamlit as st
import pandas as pd
import socket

# --- CONSTANTES GLOBALES ---
SHEET_ID = "17HdWAA_Taphajpj6l1h1zTlgIQrl6VbKIBWPZytlGgg"
MAIN_WORKSHEET_NAME = "Hoja 1"
COL_PUNTAJE = "PUNTAJE TOTAL SMARTFARM"

# --- CONFIGURACIÓN DE PROXY ---
IS_CLOUD = os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud"

def setup_proxy():
    if not IS_CLOUD:
        try:
            socket.gethostbyname("proxy.conci.com.ar")
            PROXY_URL = "http://Sdagatti:Suya%241973@proxy.conci.com.ar:8080"
            os.environ['HTTP_PROXY'] = PROXY_URL
            os.environ['HTTPS_PROXY'] = PROXY_URL
        except socket.gaierror:
            for var in ["HTTP_PROXY", "HTTPS_PROXY"]:
                if var in os.environ: del os.environ[var]
    else:
        for var in ["HTTP_PROXY", "HTTPS_PROXY"]:
            if var in os.environ: del os.environ[var]

setup_proxy()

# --- FUNCIONES DE CONEXIÓN ---

@st.cache_resource(ttl=3600)
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Error: No se encuentra la llave 'gcp_service_account' en los Secrets.")
        st.stop()

    # Copiamos los secretos
    creds = dict(st.secrets["gcp_service_account"])
    
    # --- LIMPIEZA EXTREMA DE LA LLAVE ---
    raw_key = creds.get("private_key", "")
    
    # 1. Convertir "\n" (texto) a saltos de línea reales
    fixed_key = raw_key.replace("\\n", "\n")
    
    # 2. Eliminar comillas accidentales que Streamlit a veces añade al leer TOML
    fixed_key = fixed_key.strip().strip('"').strip("'")
    
    # 3. Validar que la llave no esté vacía tras la limpieza
    if not fixed_key:
        st.error("La llave privada está vacía. Revisa los Secrets.")
        st.stop()

    creds["private_key"] = fixed_key

    try:
        # Intentar conectar
        return gspread.service_account_from_dict(creds)
    except Exception as e:
        # Mostrar el error detallado para saber si es padding o formato
        st.error(f"Fallo en la creación del cliente gspread: {e}")
        # Debug opcional: st.text(f"Longitud de llave: {len(fixed_key)}") 
        st.stop()

@st.cache_data(ttl=300)
def load_data(ws_name):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        data = sh.worksheet(ws_name).get_all_records()
        
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error cargando la hoja '{ws_name}': {e}")
        return pd.DataFrame()

