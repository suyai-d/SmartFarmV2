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

import base64

@st.cache_resource(ttl=3600)
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Error: No se encuentra la llave 'gcp_service_account' en los Secrets.")
        st.stop()

    creds = dict(st.secrets["gcp_service_account"])
    
    # --- RECONSTRUCCIÓN TOTAL DE LLAVE (Solución Definitiva) ---
    raw_key = creds.get("private_key", "")
    
    # 1. Identificar encabezado y pie
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    
    # 2. Extraer solo el contenido central (Base64 puro)
    # Quitamos encabezado, pie, comillas, saltos de línea de texto (\n) y espacios
    clean_content = raw_key.replace(header, "").replace(footer, "")
    clean_content = clean_content.replace("\\n", "").replace("\n", "").replace(" ", "").strip()
    clean_content = clean_content.strip('"').strip("'")
    
    # 3. REPARAR PADDING MATEMÁTICAMENTE
    # Base64 debe ser múltiplo de 4. Si faltan caracteres, agregamos '='
    mod = len(clean_content) % 4
    if mod > 0:
        clean_content += "=" * (4 - mod)
    
    # 4. REENSAMBLAR RSA
    # Google requiere que la llave tenga el formato oficial con saltos cada 64 caracteres
    final_key = header + "\n"
    for i in range(0, len(clean_content), 64):
        final_key += clean_content[i:i+64] + "\n"
    final_key += footer

    creds["private_key"] = final_key

    try:
        return gspread.service_account_from_dict(creds)
    except Exception as e:
        st.error(f"Fallo crítico en gspread: {e}")
        # Debug solo en caso de error para ver qué está llegando
        st.write(f"Longitud final calculada: {len(clean_content)}")
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

