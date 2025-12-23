import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# 1. Configuración de página
st.set_page_config(page_title="Gestión de Proyectos AA - Conci", layout="wide", page_icon="sf1.png")

PROJECTS_WORKSHEET_NAME = "Proyectos Analyzer"

# Estructura de estados
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
                    vals[st_col] = col_a.selectbox(f"{st_col.replace('_', ' ').title()}", STATUS_OPTIONS)
                    vals[hr_col] = col_b.number_input(f"Horas {st_col.split(' - ')[0].title()}", min_value=0.0,
                                                      step=0.5)

                if st.form_submit_button("Guardar Proyecto"):
                    info = main_df[main_df['SELECTOR'] == cli_sel].iloc[0]
                    fila = [
                        str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
                        str(info['ID CLIENTE']), str(info['CLIENTE']), str(info['SUCURSAL']),
                        str(info['CATEGORÍA DE EVALUACIÓN']), str(tipo), str(nombre_p), str(ubic),
                        str(vals[STAGES_COLS[0][0]]), float(vals[STAGES_COLS[0][1]]),
                        str(vals[STAGES_COLS[1][0]]), float(vals[STAGES_COLS[1][1]]),
                        str(vals[STAGES_COLS[2][0]]), float(vals[STAGES_COLS[2][1]])
                    ]
                    try:
                        client = get_gspread_client()
                        ws = client.open_by_key(SHEET_ID).worksheet(PROJECTS_WORKSHEET_NAME)
                        ws.append_row(fila, value_input_option='USER_ENTERED')
                        st.success("¡Proyecto Guardado!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

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
                        cur_est = str(row.get(st_col, "No Iniciado"))
                        cur_hr = float(row.get(hr_col, 0.0))
                        new_vals[st_col] = c1.selectbox(f"{st_col}", STATUS_OPTIONS, index=STATUS_OPTIONS.index(
                            cur_est) if cur_est in STATUS_OPTIONS else 0)
                        new_vals[hr_col] = c2.number_input(f"Horas {st_col}", min_value=0.0, value=cur_hr)

                    if st.form_submit_button("Actualizar"):
                        try:
                            ws = get_gspread_client().open_by_key(SHEET_ID).worksheet(PROJECTS_WORKSHEET_NAME)
                            row_num = int(idx) + 2
                            col_p = 9
                            for st_col, hr_col in STAGES_COLS:
                                ws.update_cell(row_num, col_p, str(new_vals[st_col]))
                                ws.update_cell(row_num, col_p + 1, float(new_vals[hr_col]))
                                col_p += 2
                            st.success("Actualizado");
                            st.cache_data.clear();
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")

# --- TAB 3: DASHBOARD ---
with tab3:
    p_df = normalizar_df(load_data(PROJECTS_WORKSHEET_NAME))
    c_df = normalizar_df(load_data(MAIN_WORKSHEET_NAME))

    if not p_df.empty:
        # --- FILTRO POR SUCURSAL ---
        sucursales = ["Todas"] + sorted(p_df['SUCURSAL'].unique().tolist())
        suc_sel = st.selectbox("📍 Filtrar por Sucursal:", sucursales)

        # Aplicar filtro
        df_filtered = p_df.copy()
        if suc_sel != "Todas":
            df_filtered = df_filtered[df_filtered['SUCURSAL'] == suc_sel]

        # Convertir horas a números
        hr_cols = [s[1] for s in STAGES_COLS]
        for c in hr_cols:
            df_filtered[c] = pd.to_numeric(df_filtered[c], errors='coerce').fillna(0)
        df_filtered['TOTAL_HS'] = df_filtered[hr_cols].sum(axis=1)

        st.subheader(f"📊 Resumen General: {suc_sel}")

        # --- EMBUDO DE PROYECTOS (Métricas principales) ---
        m1, m2, m3, m4 = st.columns(4)

        # 1. Total Proyectos
        total_p = len(df_filtered)
        m1.metric("Total Proyectos", total_p)

        # 2. Planificación Completada
        plan_comp = len(df_filtered[df_filtered["PLANIFICACIÓN - ESTADO"].astype(str).str.upper() == "COMPLETADO"])
        m2.metric("Planif. Lista", plan_comp, f"{int(plan_comp / total_p * 100 if total_p > 0 else 0)}%")

        # 3. Recopilación Completada
        reco_comp = len(
            df_filtered[df_filtered["RECOPILACIÓN DE DATOS - ESTADO"].astype(str).str.upper() == "COMPLETADO"])
        m3.metric("Datos Recopilados", reco_comp, f"{int(reco_comp / total_p * 100 if total_p > 0 else 0)}%")

        # 4. Informe Completado
        inf_comp = len(
            df_filtered[df_filtered["GENERACIÓN DE INFORME - ESTADO"].astype(str).str.upper() == "COMPLETADO"])
        m4.metric("Informes Listos", inf_comp, f"{int(inf_comp / total_p * 100 if total_p > 0 else 0)}%")

        # Métricas de horas debajo del embudo
        st.write(f"⏱️ **Horas totales invertidas en esta selección:** {df_filtered['TOTAL_HS'].sum():.1f} hs")

        st.divider()
        st.subheader("📌 Avance Detallado por Proyecto")

        # Mostrar solo los proyectos filtrados
        for _, row in df_filtered.iterrows():
            with st.expander(f"🔹 {row.get('CLIENTE', 'S/D')} - {row.get('NOMBRE', 'S/D')}"):
                cols_est = st.columns(3)
                for i, (st_col, hr_col) in enumerate(STAGES_COLS):
                    status = str(row.get(st_col, "No Iniciado"))
                    horas = row.get(hr_col, 0)
                    color = COLOR_MAP.get(status, "#6c757d")
                    etapa_tit = st_col.split(" - ")[0].title()

                    cols_est[i].markdown(f"""
                        <div style='background-color:{color}; color:white; padding:12px; border-radius:8px; text-align:center;'>
                            <p style='margin:0; font-size:0.8em; opacity:0.9;'>{etapa_tit}</p>
                            <h4 style='margin:0; color:white;'>{status}</h4>
                            <p style='margin:0; font-size:0.9em; font-weight:bold;'>{horas} hs</p>
                        </div>
                    """, unsafe_allow_html=True)

        st.divider()
        st.subheader("🏢 Análisis Comparativo por Sucursal")
        if not c_df.empty:
            suc_c = c_df.groupby('SUCURSAL')['ID CLIENTE'].nunique().reset_index(name='REGISTRADOS')
            # Para el gráfico final usamos p_df (sin el filtro de arriba para poder comparar)
            p_df_calc = p_df.copy()
            for c in hr_cols: p_df_calc[c] = pd.to_numeric(p_df_calc[c], errors='coerce').fillna(0)
            p_df_calc['TOTAL_HS'] = p_df_calc[hr_cols].sum(axis=1)

            suc_p = p_df_calc.groupby('SUCURSAL').agg(
                PROYECTOS=('CLIENTE', 'count'),
                HORAS=('TOTAL_HS', 'sum')
            ).reset_index()
            resumen = pd.merge(suc_c, suc_p, on='SUCURSAL', how='left').fillna(0)
            st.dataframe(resumen, use_container_width=True, hide_index=True)
            st.plotly_chart(px.bar(resumen, x='SUCURSAL', y='HORAS', title="Esfuerzo Acumulado por Sucursal",
                                   color_discrete_sequence=['#28a745']), use_container_width=True)

st.divider()
st.link_button("📂 Acceder a Carpeta de Evidencias (Drive)",
               "https://drive.google.com/drive/folders/1ojOeFXuiPof9R0qTL9BPeipig9pwOdzW?usp=sharing")
