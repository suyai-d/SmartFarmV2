import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# 1. Configuración de página
st.set_page_config(page_title="Gestión de Proyectos AA - Conci", layout="wide", page_icon="sf1.png")

PROJECTS_WORKSHEET_NAME = "Proyectos Analyzer"

# Nombres de referencia interna (siempre en MAYÚSCULAS para match con normalizar_df)
STAGES_COLS = [
    ("PLANIFICACIÓN - ESTADO", "PLANIFICACIÓN - HORAS"),
    ("RECOPILACIÓN DE DATOS - ESTADO", "RECOPILACIÓN DE DATOS - HORAS"),
    ("GENERACIÓN DE INFORME - ESTADO", "GENERACIÓN DE INFORME - HORAS")
]
STATUS_OPTIONS = ["No Iniciado", "En Proceso", "Completado"]
COLOR_MAP = {
    "Completado": "#28a745",
    "En Proceso": "#ffc107",
    "No Iniciado": "#6c757d"
}


def normalizar_df(df):
    """Limpia encabezados: quita espacios y pasa a MAYÚSCULAS."""
    if df is not None and not df.empty:
        df.columns = [str(c).strip().upper() for c in df.columns]
    return df


st.title("🚜 Proyectos Agronomy Analyzer")
tab1, tab2, tab3 = st.tabs(["➕ Registro", "✏️ Edición", "📊 Dashboard"])

# --- TAB 1: REGISTRO ---
with tab1:
    main_df = normalizar_df(load_data(MAIN_WORKSHEET_NAME))
    if not main_df.empty:
        main_df['SELECTOR'] = main_df['ID CLIENTE'].astype(str) + " - " + main_df['CLIENTE'].astype(str)
        cli_sel = st.selectbox("Seleccionar Cliente:", [""] + main_df['SELECTOR'].unique().tolist())

        if cli_sel:
            with st.form("f_reg"):
                c1, c2 = st.columns(2)
                tipo = c1.text_input("Tipo de Proyecto")
                nombre_p = c2.text_input("NOMBRE DEL PROYECTO")
                ubic = st.text_input("Ubicación")

                vals = {}
                for st_col, hr_col in STAGES_COLS:
                    col_a, col_b = st.columns([2, 1])
                    vals[st_col] = col_a.selectbox(f"{st_col.title()}", STATUS_OPTIONS)
                    vals[hr_col] = col_b.number_input(f"Horas {st_col.split(' - ')[0].title()}", min_value=0.0,
                                                      step=0.5)

                if st.form_submit_button("Guardar Proyecto"):
                    info = main_df[main_df['SELECTOR'] == cli_sel].iloc[0]
                    fila = [
                        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        info['ID CLIENTE'], info['CLIENTE'], info['SUCURSAL'], info['CATEGORÍA DE EVALUACIÓN'],
                        tipo, nombre_p, ubic,
                        vals[STAGES_COLS[0][0]], vals[STAGES_COLS[0][1]],
                        vals[STAGES_COLS[1][0]], vals[STAGES_COLS[1][1]],
                        vals[STAGES_COLS[2][0]], vals[STAGES_COLS[2][1]]
                    ]
                    client = get_gspread_client()
                    client.open_by_key(SHEET_ID).worksheet(PROJECTS_WORKSHEET_NAME).append_row(fila)
                    st.success("¡Proyecto Guardado!");
                    st.cache_data.clear();
                    st.rerun()

# --- TAB 2: EDICIÓN ---
with tab2:
    p_df = normalizar_df(load_data(PROJECTS_WORKSHEET_NAME))
    if not p_df.empty:
        if 'NOMBRE' in p_df.columns:
            p_df['SELECTOR_E'] = p_df['CLIENTE'].astype(str) + " | " + p_df['NOMBRE'].astype(str)
            sel_e = st.selectbox("Proyecto a editar:", [""] + p_df['SELECTOR_E'].tolist())

            if sel_e:
                idx = p_df[p_df['SELECTOR_E'] == sel_e].index[0]
                row = p_df.iloc[idx]
                with st.form("f_edit"):
                    st.subheader(f"Editando: {row['NOMBRE']}")
                    new_vals = {}
                    for st_col, hr_col in STAGES_COLS:
                        c1, c2 = st.columns([2, 1])
                        cur_est = row.get(st_col, "No Iniciado")
                        cur_hr = float(row.get(hr_col, 0.0))
                        new_vals[st_col] = c1.selectbox(f"{st_col}", STATUS_OPTIONS, index=STATUS_OPTIONS.index(
                            cur_est) if cur_est in STATUS_OPTIONS else 0)
                        new_vals[hr_col] = c2.number_input(f"Horas {st_col}", min_value=0.0, value=cur_hr)

                    if st.form_submit_button("Actualizar"):
                        ws = get_gspread_client().open_by_key(SHEET_ID).worksheet(PROJECTS_WORKSHEET_NAME)
                        col_p = 9
                        for st_col, hr_col in STAGES_COLS:
                            ws.update_cell(int(idx) + 2, col_p, new_vals[st_col])
                            ws.update_cell(int(idx) + 2, col_p + 1, new_vals[hr_col])
                            col_p += 2
                        st.success("Actualizado");
                        st.cache_data.clear();
                        st.rerun()
        else:
            st.error("No se detecta la columna 'NOMBRE'.")

# --- TAB 3: DASHBOARD ---
with tab3:
    p_df = normalizar_df(load_data(PROJECTS_WORKSHEET_NAME))
    c_df = normalizar_df(load_data(MAIN_WORKSHEET_NAME))

    if not p_df.empty:
        # 1. KPIs Generales
        hr_cols_upper = [s[1] for s in STAGES_COLS]
        for c in hr_cols_upper: p_df[c] = pd.to_numeric(p_df[c], errors='coerce').fillna(0)
        p_df['TOTAL_HS'] = p_df[hr_cols_upper].sum(axis=1)

        st.subheader("📊 Resumen General")
        m1, m2, m3 = st.columns(3)
        m1.metric("Proyectos Activos", len(p_df))
        m2.metric("Horas Totales", f"{p_df['TOTAL_HS'].sum():.1f} hs")
        inf_col = "GENERACIÓN DE INFORME - ESTADO"
        cerrados = len(p_df[p_df[inf_col] == "Completado"]) if inf_col in p_df.columns else 0
        m3.metric("Proyectos Cerrados", cerrados)

        # 2. SECCIÓN DE AVANCE POR CLIENTE (LO QUE FALTABA)
        st.divider()
        st.subheader("📌 Estado Detallado por Proyecto")

        for _, row in p_df.iterrows():
            cliente_nombre = row.get('CLIENTE', 'S/D')
            proyecto_nombre = row.get('NOMBRE', 'S/D')

            with st.expander(f"🔹 {cliente_nombre} - {proyecto_nombre}"):
                cols_est = st.columns(3)
                for i, (st_col, hr_col) in enumerate(STAGES_COLS):
                    status = row.get(st_col, "No Iniciado")
                    horas = row.get(hr_col, 0)
                    color = COLOR_MAP.get(status, "#6c757d")

                    # Título de la etapa simplificado para mostrar
                    etapa_tit = st_col.split(" - ")[0].title()

                    cols_est[i].markdown(f"""
                        <div style='background-color:{color}; color:white; padding:12px; border-radius:8px; text-align:center; border: 1px solid #ddd'>
                            <p style='margin:0; font-size:0.8em; opacity:0.9;'>{etapa_tit}</p>
                            <h4 style='margin:0; color:white;'>{status}</h4>
                            <p style='margin:0; font-size:0.9em; font-weight:bold;'>{horas} hs</p>
                        </div>
                    """, unsafe_allow_html=True)

        # 3. Métricas por Sucursal
        st.divider()
        st.subheader("🏢 Análisis por Sucursal")
        if not c_df.empty:
            suc_c = c_df.groupby('SUCURSAL')['ID CLIENTE'].nunique().reset_index(name='REGISTRADOS')
            suc_p = p_df.groupby('SUCURSAL').agg(
                PROYECTOS=('CLIENTE', 'count'),
                HORAS=('TOTAL_HS', 'sum')
            ).reset_index()
            resumen = pd.merge(suc_c, suc_p, on='SUCURSAL', how='left').fillna(0)
            st.dataframe(resumen, use_container_width=True, hide_index=True)
            st.plotly_chart(px.bar(resumen, x='SUCURSAL', y='HORAS', title="Esfuerzo por Sucursal",
                                   color_discrete_sequence=['#28a745']), use_container_width=True)
