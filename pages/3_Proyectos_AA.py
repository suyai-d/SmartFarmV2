import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.express as px
from datetime import datetime
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


def normalizar_df(df):
    """Limpia encabezados: quita espacios y pasa a MAYÚSCULAS."""
    if df is not None and not df.empty:
        df.columns = [str(c).strip().upper() for c in df.columns]
    return df


st.title("🚜 Proyectos Agronomy Analyzer")

# Dos pestañas: Gestión y Dashboard
tab1, tab2 = st.tabs(["✏️ Gestión de Estados", "📊 Dashboard"])

# --- TAB 1: EDICIÓN (Gestión Directa) ---
with tab1:
    p_df_raw = normalizar_df(load_data(PROJECTS_WORKSHEET_NAME))
    if not p_df_raw.empty:
        st.subheader("Actualizar datos del proyecto")
        p_df_raw['SELECTOR_E'] = p_df_raw['CLIENTE'].astype(str) + " | " + p_df_raw['NOMBRE'].astype(str)
        sel_e = st.selectbox("Seleccione el Proyecto para editar:", [""] + p_df_raw['SELECTOR_E'].tolist())

        if sel_e:
            idx = p_df_raw[p_df_raw['SELECTOR_E'] == sel_e].index[0]
            row = p_df_raw.iloc[idx]

            with st.form("f_edit"):
                st.info(f"📍 Cliente: {row['CLIENTE']} | Proyecto: {row['NOMBRE']}")

                # --- SECCIÓN 1: PLANIFICACIÓN Y REFERENCIAS ---
                c1, c2, c3, c4 = st.columns(4)

                # Selector de FY (Fiscal Year)
                cur_fy = str(row.get('FY', '26')).strip()
                fy_options = ["25", "26", "27", "28"]
                if cur_fy not in fy_options and cur_fy != "":
                    fy_options.append(cur_fy)
                new_fy = c1.selectbox("Fiscal Year (FY):", fy_options, 
                                      index=fy_options.index(cur_fy) if cur_fy in fy_options else 1)

                q_options = ["Q1", "Q2", "Q3", "Q4"]
                cur_q = str(row.get('Q PLANTEADO', 'Q1')).strip().upper()
                new_q = c2.selectbox("Trimestre (Q):", q_options,
                                     index=q_options.index(cur_q) if cur_q in q_options else 0)

                cur_id = str(row.get('ID PRUEBA', ''))
                new_id = c3.text_input("ID de la Prueba:", value=cur_id)

                cur_link = str(row.get('LINK ACCESO', ''))
                new_link = c4.text_input("Link de Acceso:", value=cur_link)

                st.divider()

                # --- SECCIÓN 2: ESTADOS Y HORAS ---
                new_vals = {}
                for st_col, hr_col in STAGES_COLS:
                    col_a, col_b = st.columns([2, 1])
                    cur_est = str(row.get(st_col, "No Iniciado"))
                    cur_hr = float(row.get(hr_col, 0.0))

                    new_vals[st_col] = col_a.selectbox(f"Estado {st_col.split(' - ')[0]}", STATUS_OPTIONS,
                                                       index=STATUS_OPTIONS.index(
                                                           cur_est) if cur_est in STATUS_OPTIONS else 0)
                    new_vals[hr_col] = col_b.number_input(f"Horas {st_col.split(' - ')[0]}", min_value=0.0,
                                                          value=cur_hr, step=0.5)

                if st.form_submit_button("💾 Guardar Todos los Cambios"):
                    try:
                        ws = get_gspread_client().open_by_key(SHEET_ID).worksheet(PROJECTS_WORKSHEET_NAME)
                        row_num = int(idx) + 2

                        # Actualizar Q (Columna 15 - O)
                        ws.update_cell(row_num, 15, new_q)

                        # Actualizar ID (Columna 16 - P)
                        ws.update_cell(row_num, 16, new_id)

                        # Actualizar Link (Columna 17 - Q)
                        ws.update_cell(row_num, 17, new_link)

                        # Actualizar FY (Columna 18 - R)
                        ws.update_cell(row_num, 18, str(new_fy))

                        # Actualizar Estados y Horas (Columnas 9 a 14)
                        col_p = 9
                        for st_col, hr_col in STAGES_COLS:
                            ws.update_cell(row_num, col_p, str(new_vals[st_col]))
                            ws.update_cell(row_num, col_p + 1, float(new_vals[hr_col]))
                            col_p += 2

                        st.success(f"¡Datos de {row['CLIENTE']} guardados correctamente!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al conectar con Google Sheets: {e}")
    else:
        st.warning("No hay proyectos disponibles.")

# --- TAB 2: DASHBOARD ---
with tab2:
    p_df = normalizar_df(load_data(PROJECTS_WORKSHEET_NAME))

    if not p_df.empty:
        # 1. FILTROS (Distribuidos en 4 columnas)
        cf1, cf2, cf3, cf4 = st.columns(4)
        
        # Filtro de FY
        fy_disponibles = sorted(p_df['FY'].astype(str).unique().tolist())
        fy_sel = cf1.selectbox("📅 Filtrar por FY:", ["Todos"] + fy_disponibles, key="filt_fy")

        # Filtro de Sucursal
        sucursales = ["Todas"] + sorted(p_df['SUCURSAL'].dropna().astype(str).unique().tolist())
        suc_sel = cf2.selectbox("📍 Filtrar por Sucursal:", sucursales, key="filt_suc")

        # Filtro de Q
        qs_disponibles = ["Todos"] + sorted(p_df['Q PLANTEADO'].dropna().astype(str).unique().tolist())
        q_sel = cf3.selectbox("⏳ Filtrar por Q:", qs_disponibles, key="filt_q")

        # Filtro por Tipo de Proyecto
        if 'TIPO DE PROYECTO' in p_df.columns:
            tipos_disponibles = ["Todos"] + sorted(p_df['TIPO DE PROYECTO'].dropna().astype(str).unique().tolist())
        else:
            tipos_disponibles = ["Todos"]
        tipo_sel = cf4.selectbox("🏷️ Tipo de Proyecto:", tipos_disponibles, key="filt_tipo")

        # Aplicación de Filtros
        df_f = p_df.copy()
        if fy_sel != "Todos":
            df_f = df_f[df_f['FY'].astype(str) == str(fy_sel)]
        if suc_sel != "Todas":
            df_f = df_f[df_f['SUCURSAL'].astype(str) == suc_sel]
        if q_sel != "Todos":
            df_f = df_f[df_f['Q PLANTEADO'].astype(str) == q_sel]
        if tipo_sel != "Todos" and 'TIPO DE PROYECTO' in df_f.columns:
            df_f = df_f[df_f['TIPO DE PROYECTO'].astype(str) == tipo_sel]

        # 2. PROCESAMIENTO
        hr_cols = [s[1] for s in STAGES_COLS]
        for c in hr_cols:
            df_f[c] = pd.to_numeric(df_f[c], errors='coerce').fillna(0)
        df_f['TOTAL_HS'] = df_f[hr_cols].sum(axis=1).round(1)

        # 3. MÉTRICAS
        total_p = len(df_f)
        inf_listos = len(df_f[df_f["GENERACIÓN DE INFORME - ESTADO"].astype(str).str.upper() == "COMPLETADO"])
        tasa_cierre = (inf_listos / total_p * 100) if total_p > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Proyectos Activos", total_p)
        m2.metric("Horas Totales", f"{df_f['TOTAL_HS'].sum():.1f}")
        m3.metric("Informes Terminados", inf_listos)
        m4.metric("Tasa de Cierre", f"{tasa_cierre:.1f}%")

        st.divider()

        # 4. GANTT
        st.subheader("📅 Cronograma de Proyectos (Gantt)")
        
        gantt_data = []
        hoy = datetime.now()

        for _, row in df_f.iterrows():
            q_val = str(row.get('Q PLANTEADO', '')).strip().upper()
            fy_val = str(row.get('FY', '26')).strip()
            
            # Determinamos el año calendario de inicio del FY (por ejemplo, FY26 -> Nov 2025)
            try:
                fy_int = int(fy_val)
                start_year = (2000 + fy_int) - 1 if fy_int < 100 else fy_int - 1
            except ValueError:
                start_year = 2025  # Fallback a FY26 si hay dato inválido

            # Fechas del Fiscal Year (Nov 1 a Oct 31)
            q_dates = {
                "Q1": (datetime(start_year, 11, 1), datetime(start_year + 1, 1, 31)),
                "Q2": (datetime(start_year + 1, 2, 1), datetime(start_year + 1, 4, 30)),
                "Q3": (datetime(start_year + 1, 5, 1), datetime(start_year + 1, 7, 31)),
                "Q4": (datetime(start_year + 1, 8, 1), datetime(start_year + 1, 10, 31))
            }

            plan_est = str(row.get("PLANIFICACIÓN - ESTADO", "")).upper()
            reco_est = str(row.get("RECOPILACIÓN DE DATOS - ESTADO", "")).upper()
            info_est = str(row.get("GENERACIÓN DE INFORME - ESTADO", "")).upper()

            if q_val in q_dates:
                start, end = q_dates[q_val]
                if info_est == "COMPLETADO":
                    recurso = "✅ Terminado"
                elif "EN PROCESO" in [plan_est, reco_est, info_est] or "COMPLETADO" in [plan_est, reco_est]:
                    recurso = "🟡 En Proceso"
                elif start <= hoy <= end:
                    recurso = "🔥 Debería estar Activo"
                else:
                    recurso = "⏳ Pendiente"

                gantt_data.append(
                    dict(Task=f"{row['CLIENTE']} - {row['NOMBRE']} (FY{fy_val})", Start=start, Finish=end, Resource=recurso))

        if gantt_data:
            df_gantt = pd.DataFrame(gantt_data)
            colors_gantt = {"✅ Terminado": "#28a745", "🟡 En Proceso": "#ffc107", "🔥 Debería estar Activo": "#dc3545",
                            "⏳ Pendiente": "#6c757d"}
            fig_gantt = ff.create_gantt(df_gantt, colors=colors_gantt, index_col='Resource', show_colorbar=True,
                                        group_tasks=True, showgrid_x=True)
            altura_g = max(450, len(df_gantt) * 35)
            fig_gantt.update_layout(height=altura_g, margin=dict(t=30, b=30, l=200))
            fig_gantt.add_vline(x=hoy.timestamp() * 1000, line_dash="dash", line_color="orange", annotation_text="HOY")
            st.plotly_chart(fig_gantt, use_container_width=True)
        else:
            st.info("No se encontraron proyectos para los filtros seleccionados.")

        st.divider()

        # 5. TABLA SEMAFÓRICA (Con ID, Link, FY y Tipo de Proyecto)
        st.subheader("📌 Listado Maestro de Proyectos")

        def style_estados_fuerte(val):
            v = str(val).upper()
            if v == "COMPLETADO": return "background-color: #28a745; color: white; font-weight: bold;"
            if v == "EN PROCESO": return "background-color: #ffc107; color: black; font-weight: bold;"
            if v == "NO INICIADO": return "background-color: #dc3545; color: white; font-weight: bold;"
            return ""

        cols_est_names = [s[0] for s in STAGES_COLS]
        
        base_cols = ['FY', 'CLIENTE', 'NOMBRE']
        if 'TIPO DE PROYECTO' in df_f.columns:
            base_cols.append('TIPO DE PROYECTO')
        base_cols += ['SUCURSAL', 'Q PLANTEADO', 'ID PRUEBA', 'LINK ACCESO']
        
        cols_mostrar = base_cols + cols_est_names + ['TOTAL_HS']

        df_styled = df_f[cols_mostrar].style.applymap(style_estados_fuerte, subset=cols_est_names)

        column_config = {
            "FY": st.column_config.TextColumn("FY", help="Año Fiscal del Proyecto"),
            "TIPO DE PROYECTO": st.column_config.TextColumn("Tipo", help="Tipo de Proyecto / Producto"),
            "TOTAL_HS": st.column_config.NumberColumn("Hs Totales", format="%.1f ⏳"),
            "LINK ACCESO": st.column_config.LinkColumn(
                "Enlace",
                help="Acceso directo a la prueba",
                display_text="🔗 Abrir"
            ),
            "ID PRUEBA": st.column_config.TextColumn("ID Prueba", help="ID único de la prueba en el sistema"),
            "Q PLANTEADO": "Trimestre",
            "PLANIFICACIÓN - ESTADO": "Planif.",
            "RECOPILACIÓN DE DATOS - ESTADO": "Datos",
            "GENERACIÓN DE INFORME - ESTADO": "Informe"
        }

        st.dataframe(
            df_styled,
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

        # 6. GRÁFICOS FINALES
        st.subheader("📊 Análisis de Esfuerzo")
        g1, g2 = st.columns(2)

        with g1:
            suc_hs = df_f.groupby('SUCURSAL')['TOTAL_HS'].sum().reset_index().sort_values('TOTAL_HS', ascending=False)
            st.plotly_chart(px.bar(suc_hs, x='SUCURSAL', y='TOTAL_HS', title="Horas por Sucursal", text_auto='.1f',
                                   color_discrete_sequence=['#28a745']), use_container_width=True)

        with g2:
            dict_hs_etapas = {
                "Planificación": df_f["PLANIFICACIÓN - HORAS"].sum(),
                "Recopilación Datos": df_f["RECOPILACIÓN DE DATOS - HORAS"].sum(),
                "Generación Informe": df_f["GENERACIÓN DE INFORME - HORAS"].sum()
            }
            df_pie = pd.DataFrame(list(dict_hs_etapas.items()), columns=['Etapa', 'Horas'])
            st.plotly_chart(px.pie(df_pie, values='Horas', names='Etapa', title="Horas por Etapa", hole=0.4,
                                   color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)

st.divider()
st.link_button("📂 Carpeta de Evidencias",
               "https://drive.google.com/drive/folders/1ojOeFXuiPof9R0qTL9BPeipig9pwOdzW?usp=sharing")
