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

    creds = dict(st.secrets["gcp_service_account"])
    
    # --- REPARACIÓN AVANZADA DE LLAVE PRIVADA ---
    raw_key = creds.get("private_key", "")
    
    # 1. Limpieza inicial
    fixed_key = raw_key.replace("\\n", "\n").strip().strip('"').strip("'")
    
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    
    if header in fixed_key and footer in fixed_key:
        # 2. Normalización de contenido Base64
        content = fixed_key.replace(header, "").replace(footer, "")
        content = "".join(content.split()) # Quita espacios y saltos invisibles
        
        # 3. Reparar Padding (relleno =)
        missing_padding = len(content) % 4
        if missing_padding:
            content += "=" * (4 - missing_padding)
            
        # 4. Reconstrucción con formato RSA estándar
        lines = [content[i:i+64] for i in range(0, len(content), 64)]
        fixed_key = header + "\n" + "\n".join(lines) + "\n" + footer

    creds["private_key"] = fixed_key

    try:
        return gspread.service_account_from_dict(creds)
    except Exception as e:
        st.error(f"Fallo en la creación del cliente gspread: {e}")
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
        # Normalización de columnas para evitar KeyErrors
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error cargando la hoja '{ws_name}': {e}")
        return pd.DataFrame()
