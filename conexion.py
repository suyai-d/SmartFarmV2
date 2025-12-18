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

    # --- LIMPIEZA POR EXPRESIÓN REGULAR ---
    # 1. Extraer solo lo que está entre los guiones (el cuerpo de la llave)
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    
    # Buscamos el contenido base64 ignorando encabezado y pie
    content_match = re.search(f"{header}(.*?){footer}", raw_key, re.DOTALL)
    
    if content_match:
        content = content_match.group(1)
    else:
        # Si no hay guiones, tratamos toda la cadena como contenido
        content = raw_key

    # 2. Filtrar: Quedarse SOLO con caracteres A-Z, a-z, 0-9, +, / y =
    # Esto elimina \n, espacios, comillas, barras invertidas, etc.
    content = "".join(re.findall(r'[A-Za-z0-9+/=]', content))

    # 3. Reparar Padding (El corazón del error)
    # Base64 requiere que la longitud sea múltiplo de 4
    while len(content) % 4 != 0:
        content += "="

    # 4. Reconstrucción RSA Estándar (Saltos de línea cada 64 caracteres)
    formatted_content = "\n".join([content[i:i+64] for i in range(0, len(content), 64)])
    fixed_key = f"{header}\n{formatted_content}\n{footer}"

    creds["private_key"] = fixed_key

    try:
        return gspread.service_account_from_dict(creds)
    except Exception as e:
        st.error(f"Error persistente en gspread: {e}")
        # Muestra los primeros y últimos 10 caracteres para verificar que no esté vacía
        if len(content) > 20:
            st.info(f"Diagnóstico: Llave procesada correctamente ({len(content)} chars).")
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


