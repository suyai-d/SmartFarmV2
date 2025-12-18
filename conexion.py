import os
import gspread
import streamlit as st
import pandas as pd
import socket

# --- CONSTANTES GLOBALES ---
SHEET_ID = "17HdWAA_Taphajpj6l1h1zTlgIQrl6VbKIBWPZytlGgg"
MAIN_WORKSHEET_NAME = "Hoja 1"
COL_PUNTAJE = "PUNTAJE TOTAL SMARTFARM"

# --- CONFIGURACIÓN DE PROXY INTELIGENTE (CORREGIDA) ---
IS_CLOUD = os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud"


def setup_proxy():
    if not IS_CLOUD:
        # Intentamos resolver la dirección del proxy para ver si estamos en la red de Conci
        try:
            # Si esto falla, es que no estamos en la red de la oficina
            socket.gethostbyname("proxy.conci.com.ar")

            # Si llegamos aquí, aplicamos el proxy (Nota: %24 es el escape para el $)
            PROXY_URL = "http://Sdagatti:Suya%241973@proxy.conci.com.ar:8080"
            os.environ['HTTP_PROXY'] = PROXY_URL
            os.environ['HTTPS_PROXY'] = PROXY_URL
            # st.sidebar.success("Conectado vía Proxy Conci") # Opcional para debug
        except socket.gaierror:
            # Si falla, limpiamos variables por si acaso y vamos directo
            for var in ["HTTP_PROXY", "HTTPS_PROXY"]:
                if var in os.environ: del os.environ[var]
            # st.sidebar.info("Conexión directa (Sin Proxy)") # Opcional para debug
    else:
        # En la nube eliminamos cualquier rastro de proxy
        for var in ["HTTP_PROXY", "HTTPS_PROXY"]:
            if var in os.environ: del os.environ[var]


setup_proxy()


# --- FUNCIONES DE CONEXIÓN ---

@st.cache_resource(ttl=3600)
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Error: No se encuentra la llave 'gcp_service_account' en los Secrets.")
        st.stop()

    # Creamos una copia para no romper los secretos originales
    creds = dict(st.secrets["gcp_service_account"])

    # --- LIMPIEZA DE LLAVE PRIVADA (Solución definitiva al Padding/Binascii) ---
    raw_key = creds.get("private_key", "")

    # 1. Convertir los \n de texto a saltos de línea reales
    fixed_key = raw_key.replace("\\n", "\n")

    # 2. Limpiar espacios, comillas accidentales y saltos al inicio/final
    fixed_key = fixed_key.strip().strip('"').strip("'")

    # 3. Asegurar que la llave tenga los saltos de línea correctos si se pegó como una sola línea
    if "-----BEGIN PRIVATE KEY-----" in fixed_key and "\n" not in fixed_key.replace("-----BEGIN PRIVATE KEY-----", ""):
        fixed_key = fixed_key.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        fixed_key = fixed_key.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")

    creds["private_key"] = fixed_key

    return gspread.service_account_from_dict(creds)


@st.cache_data(ttl=300)
def load_data(ws_name):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        # Cargamos los datos
        data = sh.worksheet(ws_name).get_all_records()
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        # Normalizamos columnas
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        # Si el error es de autenticación, suele ser la llave o el permiso de la hoja
        st.error(f"Error en {ws_name}: {e}")
        return pd.DataFrame()
