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

import re

@st.cache_resource(ttl=3600)
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Error: No se encuentra la llave 'gcp_service_account' en los Secrets.")
        st.stop()

    creds = dict(st.secrets["gcp_service_account"])
    raw_key = creds.get("private_key", "")

    # 1. Limpieza total con Regex
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    
    # Extraemos el contenido entre guiones
    content_match = re.search(f"{header}(.*?){footer}", raw_key, re.DOTALL)
    content = content_match.group(1) if content_match else raw_key

    # Solo caracteres validos de Base64
    content = "".join(re.findall(r'[A-Za-z0-9+/=]', content))

    # 2. ALERTA DE LONGITUD (Puntual para tu error actual)
    if len(content) < 1000:
        st.error(f"⚠️ La llave es demasiado corta ({len(content)} caracteres). Debe tener aprox. 1600. Por favor, vuelve a copiarla completa del JSON original.")
        st.stop()

    # 3. Reparar Padding
    while len(content) % 4 != 0:
        content += "="

    # 4. Formatear para Google
    formatted_content = "\n".join([content[i:i+64] for i in range(0, len(content), 64)])
    creds["private_key"] = f"{header}\n{formatted_content}\n{footer}"

    try:
        return gspread.service_account_from_dict(creds)
    except Exception as e:
        st.error(f"Error persistente en gspread: {e}")
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



