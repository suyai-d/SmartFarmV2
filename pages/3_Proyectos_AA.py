import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import gspread
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# 1. Configuración de página
st.set_page_config(
    page_title="Gestión de Proyectos AA - Conci",
    layout="wide",
    page_icon="sf1.png"
)

# --- CONSTANTES ---
PROJECTS_WORKSHEET_NAME = "Proyectos Analyzer"
PROJECT_TYPES = [
    "AutoPath", "Autotrac Turn Automation", "ExactApply", "Grain Sensing",
    "Harvest Lab", "Machine Sync", "Pulverizadora PLA", "Sembradora JD",
    "Sembradora PLA", "S7 Automation", "S700 Combine Advisor"
]
PROJECT_STAGES = ["Planificación", "Recopilación de Datos", "Generación de informe"]
STAGE_STATUS_OPTIONS = ["No Iniciado", "En Proceso", "Completado"]

COLOR_MAP = {
    "Completado": "#28a745",
    "En Proceso": "#ffc107",
    "No Iniciado": "#6c757d",
    "Pendiente": "#6c757d"
}


# --- FUNCIONES DE DATOS ---

@st.cache_data(ttl=60)
def get_projects_data():
    """Carga datos de proyectos y calcula métricas de progreso."""
    try:
        df = load_data(PROJECTS_WORKSHEET_NAME)
        if df.empty: return df

        # Conversión de horas y cálculo de estado global
        df['Horas Totales'] = 0
        for stage in PROJECT_STAGES:
            h_col = f"{stage} - Horas"
            df[h_col] = pd.to_numeric(df[h_col], errors='coerce').fillna(0)
            df['Horas Totales'] += df[h_col]

        # Row index para actualizaciones (Sheets empieza en 1, +1 por encabezado)
        df['__row'] = df.index + 2
        return df
    except:
        return pd.DataFrame()


def save_new_project(data):
    """Guarda una nueva fila en la pestaña de proyectos."""
    try:
        client = get_gspread_client()
        ws = client.open_by_key(SHEET_ID).worksheet(PROJECTS_WORKSHEET_NAME)
        ws.append_row(list(data.values()))
        get_projects_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False


# --- INTERFAZ ---

st.title("🚜 Proyectos Agronomy Analyzer")

tab1, tab2, tab3 = st.tabs(["➕ Registro", "✏️ Edición", "📊 Dashboard"])

# --- TAB 1: REGISTRO ---
with tab1:
    main_df = load_data(MAIN_WORKSHEET_NAME)
    if not main_df.empty:
        # Selector de cliente desde la base principal
        main_df['Selector'] = main_df['ID Cliente'].astype(str) + " - " + main_df['Cliente']
        cli_sel = st.selectbox("Seleccionar Cliente:", [""] + main_df['Selector'].unique().tolist())

        if cli_sel:
            with st.form("form_registro"):
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("Tipo de Proyecto", PROJECT_TYPES)
                nombre = c2.text_input("Nombre del Proyecto (Ej: Mapa Cosecha 2024)")
                loc = st.text_input("Ubicación/Lote")

                st.write("---")
                st.write("⏱️ Carga Inicial de Horas")
                # Generamos dinámicamente campos para cada etapa
                horas_init = {}
                for stage in PROJECT_STAGES:
                    horas_init[f"{stage} - Estado"] = "No Iniciado"
                    horas_init[f"{stage} - Horas"] = st.number_input(f"Horas en {stage}", min_value=0.0, step=0.5)

                if st.form_submit_button("Guardar Proyecto"):
                    info_cli = main_df[main_df['Selector'] == cli_sel].iloc[0]
                    nuevo_p = {
                        "Fecha": datetime.now().strftime("%d/%m/%Y"),
                        "ID Cliente": info_cli['ID Cliente'],
                        "Cliente": info_cli['Cliente'],
                        "Sucursal": info_cli['Sucursal'],
                        "Tipo": tipo,
                        "Nombre": nombre,
                        "Ubicación": loc,
                        **horas_init
                    }
                    if save_new_project(nuevo_p):
                        st.success("Proyecto registrado!")
                        st.rerun()

# --- TAB 3: DASHBOARD ---
with tab3:
    proj_df = get_projects_data()
    if not proj_df.empty:
        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Proyectos", len(proj_df))
        k2.metric("Horas Totales", f"{proj_df['Horas Totales'].sum():.1f} hs")
        k3.metric("Clientes Activos", proj_df['ID Cliente'].nunique())

        # Gráfico de carga por etapa

        st.subheader("Estado de Proyectos por Cliente")
        for idx, row in proj_df.iterrows():
            with st.expander(f"📌 {row['Cliente']} - {row['Nombre']}"):
                cols = st.columns(3)
                for i, stage in enumerate(PROJECT_STAGES):
                    status = row[f"{stage} - Estado"]
                    color = COLOR_MAP.get(status, "#6c757d")
                    cols[i].markdown(f"""
                        <div style='background-color:{color}; color:white; padding:10px; border-radius:5px; text-align:center'>
                            <b>{stage}</b><br>{status}
                        </div>
                    """, unsafe_allow_html=True)
