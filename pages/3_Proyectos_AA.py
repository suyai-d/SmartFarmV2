import streamlit as st
import gspread
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from conexion import load_data, SHEET_ID, MAIN_WORKSHEET_NAME, COL_PUNTAJE

# -----------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y PROXY
# -----------------------------------------------------------
st.set_page_config(
    page_title="SmartFarm - Conci",
    layout="wide",
    page_icon="sf1.png",
    initial_sidebar_state="collapsed",
)

PROJECT_TYPES = [
    "AutoPath", "Autotrac Turn Automation", "ExactApply", "Grain Sensing",
    "Harvest Lab", "Machine Sync", "Pulverizadora PLA", "Sembradora JD",
    "Sembradora PLA", "S7 Automation", "S700 Combine Advisor"
]
PROJECT_STAGES = ["Planificación", "Recopilación de Datos", "Generación de informe"]
STAGE_STATUS_OPTIONS = ["No Iniciado", "En Proceso", "Completado"]

# Colores para la visualización de progreso
COLOR_MAP = {
    "Completado": "#28a745",  # Verde
    "En Proceso": "#ffc107",  # Amarillo
    "No Iniciado": "#6c757d",  # Gris
    "Pendiente": "#6c757d"  # Gris
}


# -----------------------------------------------------------
# FUNCIONES DE CONEXIÓN Y DATOS
# -----------------------------------------------------------

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Autentica el cliente de gspread."""
    creds_json = st.secrets["gcp_service_account"]
    return gspread.service_account_from_dict(creds_json)


@st.cache_data(ttl=300)
def load_worksheet_data(worksheet_name, force_reload_key=0):
    """Carga y devuelve todos los datos de una hoja específica en un DataFrame. (Usado para la Hoja 1)"""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        _ = force_reload_key
        return pd.DataFrame(data)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar datos de {worksheet_name}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)  # Cache corto para reflejar cambios recientes
def get_projects_data_for_ui(force_reload_key=0):
    """Carga datos de proyectos, incluyendo el índice de fila de Sheets para edición y cálculos."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(PROJECTS_WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if df.empty:
            return df

        # Conversión de horas a float (necesario para sumar)
        for stage in PROJECT_STAGES:
            hours_key = f"{stage} - Horas"
            if hours_key in df.columns:
                df[hours_key] = pd.to_numeric(df[hours_key], errors='coerce').fillna(0.0)

        # 1. Índice de fila para edición
        df['__sheet_row_index'] = df.index + 2

        # 2. Calcular el estado global
        def get_global_status(row):
            estados = [
                row.get("Planificación - Estado", "No Iniciado"),
                row.get("Recopilación de Datos - Estado", "No Iniciado"),
                row.get("Generación de informe - Estado", "No Iniciado")
            ]
            if all(s == "Completado" for s in estados):
                return "Completado"
            elif "En Proceso" in estados:
                return "En Proceso"
            else:
                return "Pendiente"

        df['Estado Global'] = df.apply(get_global_status, axis=1)

        # 3. Calcular Horas Totales
        df['Horas Totales'] = df[[f"{s} - Horas" for s in PROJECT_STAGES]].sum(axis=1)

        _ = force_reload_key
        return df
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar proyectos: {e}")
        return pd.DataFrame()


def save_project_data(project_data):
    """Guarda el nuevo proyecto en la hoja 'Proyectos Analyzer'."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(PROJECTS_WORKSHEET_NAME)
        row_data = list(project_data.values())
        worksheet.append_row(row_data)
        get_projects_data_for_ui.clear()
        return True
    except gspread.WorksheetNotFound:
        st.error(f"Error al guardar: La hoja '{PROJECTS_WORKSHEET_NAME}' no fue encontrada.")
        return False
    except Exception as e:
        st.error(f"Error al guardar los datos del proyecto: {e}")
        return False


def update_project_stages(sheet_row_index, new_stage_data):
    """Actualiza el estado y horas de las etapas de un proyecto existente."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(PROJECTS_WORKSHEET_NAME)

        cols_to_update = [
            "Planificación - Estado", "Planificación - Horas",
            "Recopilación de Datos - Estado", "Recopilación de Datos - Horas",
            "Generación de informe - Estado", "Generación de informe - Horas"
        ]

        headers = worksheet.row_values(1)

        for col_name in cols_to_update:
            if col_name in new_stage_data:
                col_index = headers.index(col_name) + 1
                new_value = new_stage_data[col_name]

                if isinstance(new_value, float):
                    new_value = f"{new_value:.2f}"

                worksheet.update_cell(sheet_row_index, col_index, new_value)

        get_projects_data_for_ui.clear()
        return True
    except gspread.WorksheetNotFound:
        st.error(f"Error al actualizar: La hoja '{PROJECTS_WORKSHEET_NAME}' no fue encontrada.")
        return False
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False


def get_stage_status_html(status, stage_name):
    """Genera el HTML para el estado de una etapa con el color correspondiente."""
    color = COLOR_MAP.get(status, COLOR_MAP['No Iniciado'])
    text = f"**{stage_name}**"

    # Crear un contenedor con fondo coloreado y texto blanco/oscuro para contraste
    style = f"""
        padding: 5px; 
        margin: 2px 0; 
        border-radius: 4px; 
        text-align: center; 
        background-color: {color}; 
        color: {'#000000' if color == '#ffc107' else '#FFFFFF'};
    """

    # Mostrar solo el estado abreviado dentro de la barra simulada
    status_abbr = status[0]

    return f'<div style="{style}">{status_abbr}</div>'


# -----------------------------------------------------------
# INTERFAZ DE STREAMLIT
# -----------------------------------------------------------

st.title("🚜 Proyectos Agronomy Analyzer")
st.markdown("Gestione el registro, edición y seguimiento de los proyectos tecnológicos.")

# --- CARGA INICIAL DE CLIENTES Y PROYECTOS ---
main_df = load_worksheet_data(MAIN_WORKSHEET_NAME)
projects_df = get_projects_data_for_ui()

if main_df.empty:
    st.error("No se pudieron cargar los clientes de la Hoja 1. Verifique el nombre y el contenido de la hoja.")
    st.stop()

# --- DEFINICIONES DE SELECCIÓN GLOBALES ---

# Crear columna de selección combinada 'Cliente ID'
if 'ID Cliente' in main_df.columns and 'Cliente' in main_df.columns:
    # Aseguramos conversión a string para evitar TypeErrors si algún ID es numérico
    main_df['Cliente ID'] = (
            main_df['ID Cliente'].astype(str) +
            ' - ' +
            main_df['Cliente'].astype(str)
    )
    client_options = ['Selecciona un cliente'] + main_df['Cliente ID'].unique().tolist()
    total_unique_clients = main_df['ID Cliente'].nunique()
else:
    st.error("Error: Las columnas 'ID Cliente' o 'Cliente' no se encontraron en la Hoja 1.")
    st.stop()

# --- FIN DE DEFINICIONES GLOBALES ---


# -----------------------------------------------------------
# PESTAÑAS DE NAVEGACIÓN
# -----------------------------------------------------------

tab_register, tab_edit, tab_tracker = st.tabs([
    "➕ Registrar Proyecto",
    "✏️ Editar Progreso",
    "📊 Tablero de Seguimiento"
])

# ===========================================================
# PESTAÑA 1: REGISTRAR NUEVO PROYECTO
# ===========================================================

with tab_register:
    st.header("1. Registrar Nuevo Proyecto")

    with st.form("register_form", clear_on_submit=True):
        st.subheader("Selección del Cliente")

        col1, col2 = st.columns([3, 1])

        selected_client_combined = col1.selectbox(
            "Seleccionar Cliente (ID - Nombre)",
            options=client_options,
            key='reg_client_select'
        )

        current_client_data = {}
        show_registration_fields = False

        if selected_client_combined != 'Selecciona un cliente':
            id_cliente = selected_client_combined.split(' - ')[0]
            client_record = main_df[main_df['ID Cliente'].astype(str) == id_cliente].iloc[-1]

            current_client_data = {
                "ID Cliente": id_cliente,
                "Cliente": client_record['Cliente'],
                "Sucursal": client_record['Sucursal'],
                "Categoría": client_record['Categoría de evaluación'],
            }

            col2.metric(label="Sucursal", value=current_client_data["Sucursal"])
            st.metric(label="Categoría de Evaluación", value=current_client_data["Categoría"])
            st.markdown("---")
            show_registration_fields = True

        if show_registration_fields:
            # --- CAMPOS DE REGISTRO ---
            st.header("2. Detalles del Proyecto")

            col3, col4 = st.columns(2)

            project_type = col3.selectbox(
                "Tipo de Proyecto (Agronomy Analyzer)",
                options=PROJECT_TYPES,
                key='reg_project_type'
            )

            project_name = col4.text_input(
                "Nombre o Evaluación del Proyecto",
                key='reg_project_name'
            )

            project_location = st.text_input(
                "Ubicación del Proyecto (Ej: Lote San Roque, Estancia La Pampa)",
                key='reg_project_location'
            )

            st.markdown("---")
            st.header("3. Seguimiento de Etapas y Horas Iniciales")

            stage_data_reg = {}

            for stage in PROJECT_STAGES:
                st.subheader(f"🛠️ Etapa: {stage}")

                col_s1, col_s2 = st.columns(2)

                status_key = f"{stage} - Estado"
                hours_key = f"{stage} - Horas"

                with col_s1:
                    stage_data_reg[status_key] = st.radio(
                        "Estado",
                        options=STAGE_STATUS_OPTIONS,
                        key=f'reg_{status_key}',
                        index=0,
                        horizontal=True
                    )

                with col_s2:
                    stage_data_reg[hours_key] = st.number_input(
                        "Horas Invertidas (0.25 = 15min)",
                        min_value=0.0,
                        value=0.0,
                        step=0.25,
                        format="%.2f",
                        key=f'reg_{hours_key}'
                    )

                st.markdown("---")
        else:
            # Inicialización segura
            project_name = ""
            project_location = ""
            stage_data_reg = {f"{s} - Estado": STAGE_STATUS_OPTIONS[0] for s in PROJECT_STAGES}

        # BOTÓN DE GUARDADO
        submitted = st.form_submit_button("💾 Registrar Proyecto Completo")

        if submitted:
            if selected_client_combined == 'Selecciona un cliente':
                st.error("❌ Error: Debe seleccionar un cliente válido en el paso 1.")
            elif not project_name or not project_location:
                st.error("❌ Error: Los campos 'Nombre del Proyecto' y 'Ubicación' no pueden estar vacíos.")
            else:
                try:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    data_to_save = {
                        "Fecha y Hora": current_time,
                        "ID Cliente": current_client_data["ID Cliente"],
                        "Cliente": current_client_data["Cliente"],
                        "Sucursal": current_client_data["Sucursal"],
                        "Categoría": current_client_data["Categoría"],
                        "Tipo de Proyecto": project_type,
                        "Nombre del Proyecto": project_name,
                        "Ubicación": project_location,
                        **stage_data_reg
                    }

                    if save_project_data(data_to_save):
                        st.success(
                            f"✅ Proyecto '{project_name}' registrado con éxito para {current_client_data['Cliente']}.")

                except Exception as e:
                    st.error(f"❌ Error al procesar el guardado: {e}")

# ===========================================================
# PESTAÑA 2: EDITAR PROGRESO
# ===========================================================

with tab_edit:
    st.header("1. Seleccionar Proyecto a Editar")

    if projects_df.empty:
        st.info("No hay proyectos registrados para editar.")
    else:
        # CORRECCIÓN: Aseguramos que todas las partes sean strings para evitar TypeError
        projects_df['Proyecto ID Combinado'] = (
                projects_df['Cliente'].astype(str) + ' - ' +
                projects_df['Nombre del Proyecto'].astype(str) +
                ' (' + projects_df['Fecha y Hora'].astype(str) + ')'
        )

        edit_options = ['Selecciona un proyecto'] + projects_df['Proyecto ID Combinado'].tolist()

        selected_project_combined = st.selectbox(
            "📝 Proyecto",
            options=edit_options,
            key='edit_project_select'
        )

        if selected_project_combined != 'Selecciona un proyecto':

            selected_record = projects_df[
                projects_df['Proyecto ID Combinado'] == selected_project_combined
                ].iloc[0]

            sheet_row_index = selected_record['__sheet_row_index']

            st.markdown("---")
            st.subheader(
                f"Progreso actual: {selected_record['Estado Global']} (Tipo: {selected_record['Tipo de Proyecto']})")

            with st.form("edit_form"):
                st.header("2. Actualizar Etapas y Horas")

                stage_data_edit = {}

                for stage in PROJECT_STAGES:
                    status_key = f"{stage} - Estado"
                    hours_key = f"{stage} - Horas"

                    current_status = selected_record.get(status_key, STAGE_STATUS_OPTIONS[0])
                    current_hours = float(selected_record.get(hours_key, 0.0))

                    st.subheader(f"🛠️ Etapa: {stage}")
                    col_e1, col_e2 = st.columns(2)

                    with col_e1:
                        status_index = STAGE_STATUS_OPTIONS.index(current_status)
                        stage_data_edit[status_key] = st.radio(
                            "Estado",
                            options=STAGE_STATUS_OPTIONS,
                            key=f'edit_{status_key}',
                            index=status_index,
                            horizontal=True
                        )

                    with col_e2:
                        stage_data_edit[hours_key] = st.number_input(
                            "Horas Invertidas (0.25 = 15min)",
                            min_value=0.0,
                            value=current_hours,
                            step=0.25,
                            format="%.2f",
                            key=f'edit_{hours_key}'
                        )
                    st.markdown("---")

                edited = st.form_submit_button("✅ Guardar Cambios de Progreso")

                if edited:
                    if update_project_stages(sheet_row_index, stage_data_edit):
                        st.success(
                            f"✅ Progreso del proyecto '{selected_record['Nombre del Proyecto']}' actualizado con éxito.")
                        st.rerun()
        else:
            st.info("Seleccione un proyecto de la lista desplegable.")

# ===========================================================
# PESTAÑA 3: TABLERO DE SEGUIMIENTO (ANALYSIS Y FILTROS)
# ===========================================================

with tab_tracker:
    st.header("📊 Tablero de Análisis de Proyectos")

    if projects_df.empty:
        st.info("No hay proyectos registrados para mostrar en el seguimiento.")
    else:
        # --- 1. CONTROLES DE FILTRO ---
        st.subheader("Controles de Filtro")
        col_f1, col_f2, col_f3 = st.columns(3)

        all_sucursales = ['Todos'] + projects_df['Sucursal'].unique().tolist()
        all_types = ['Todos'] + projects_df['Tipo de Proyecto'].unique().tolist()
        all_status = ['Todos'] + projects_df['Estado Global'].unique().tolist()

        selected_sucursal = col_f1.selectbox("Filtrar por Sucursal", all_sucursales)
        selected_type = col_f2.selectbox("Filtrar por Tipo de Proyecto", all_types)
        selected_status = col_f3.selectbox("Filtrar por Estado Global", all_status)

        # Aplicar filtros
        filtered_df = projects_df.copy()

        if selected_sucursal != 'Todos':
            filtered_df = filtered_df[filtered_df['Sucursal'] == selected_sucursal]
        if selected_type != 'Todos':
            filtered_df = filtered_df[filtered_df['Tipo de Proyecto'] == selected_type]
        if selected_status != 'Todos':
            filtered_df = filtered_df[filtered_df['Estado Global'] == selected_status]

        st.markdown("---")

        if filtered_df.empty:
            st.warning("No se encontraron proyectos que coincidan con los filtros seleccionados.")
        else:

            # --- 2. MÉTRICAS CLAVE (KPIs) ---
            st.subheader("Indicadores Clave de Rendimiento (KPIs)")

            total_projects_filtered = len(filtered_df)
            total_hours = filtered_df['Horas Totales'].sum()
            completed_projects = len(filtered_df[filtered_df['Estado Global'] == 'Completado'])

            completion_rate = (completed_projects / total_projects_filtered) * 100 if total_projects_filtered > 0 else 0

            # Nuevo KPI: Tasa de penetración (Proyectos registrados / Clientes totales)
            projects_generated = len(projects_df)
            penetration_rate = (projects_generated / total_unique_clients) * 100 if total_unique_clients > 0 else 0

            col_k1, col_k2, col_k3, col_k4 = st.columns(4)

            with col_k1:
                st.metric("Total Proyectos (Filtro)", value=total_projects_filtered)
            with col_k2:
                st.metric("Total Horas Inv.", value=f"{total_hours:,.2f} hs")
            with col_k3:
                st.metric("Tasa de Finalización", value=f"{completion_rate:.1f}%")
            with col_k4:
                st.metric("Tasa de Proyectos",
                          value=f"{projects_generated} / {total_unique_clients} ({penetration_rate:.1f}%)",
                          help="Proyectos registrados del total de clientes únicos en la Hoja 1."
                          )

            st.markdown("---")

            # --- 3. GRÁFICO DE DISTRIBUCIÓN DE HORAS POR ETAPA ---
            st.subheader("Distribución de Horas por Etapa (Acumulado)")

            stage_hours = {
                'Etapa': PROJECT_STAGES,
                'Horas': [
                    filtered_df[f"{s} - Horas"].sum()
                    for s in PROJECT_STAGES
                ]
            }
            hours_df = pd.DataFrame(stage_hours)

            fig = px.bar(
                hours_df,
                x='Etapa',
                y='Horas',
                title='Horas Acumuladas por Etapa de Proyecto',
                color_discrete_sequence=['#4CAF50'],
                text='Horas'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', xaxis_title=None)

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # --- 4. TABLA DETALLADA ---
            st.subheader("Tabla Detallada de Proyectos")

            display_df = filtered_df[[
                'Cliente',
                'Sucursal',
                'Categoría',
                'Nombre del Proyecto',
                'Tipo de Proyecto',
                'Estado Global',
                'Horas Totales',
                'Planificación - Estado',
                'Recopilación de Datos - Estado',
                'Generación de informe - Estado',
            ]].rename(columns={
                'Cliente': 'Cliente',
                'Sucursal': 'Sucursal',
                'Categoría': 'Categoría',
                'Nombre del Proyecto': 'Proyecto',
                'Tipo de Proyecto': 'Tipo',
                'Estado Global': 'Estado General',
                'Horas Totales': 'Total Horas',
                'Planificación - Estado': 'Planificación',
                'Recopilación de Datos - Estado': 'Recopilación',
                'Generación de informe - Estado': 'Informe',
            })

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")

            # --- 5. LISTADO DE PROGRESO POR PROYECTO (BARRA DE COLORES) ---
            st.header("Listado de Proyectos por Cliente y Progreso")
            st.markdown(f"""
                <div style='display: flex; justify-content: space-around; width: 100%; font-weight: bold; padding: 10px 0;'>
                    <span style='width: 35%;'>Cliente / Proyecto</span>
                    <span style='width: 20%; text-align: center;'>Planificación</span>
                    <span style='width: 20%; text-align: center;'>Recopilación</span>
                    <span style='width: 20%; text-align: center;'>Informe</span>
                </div>
                <hr style='margin: 0;'>
            """, unsafe_allow_html=True)

            # Agrupar por cliente para el listado final
            grouped_clients = filtered_df.sort_values(by='Cliente').groupby('Cliente')

            # Iterar sobre clientes y proyectos
            for client_name, client_projects in grouped_clients:
                st.subheader(f"👤 {client_name}")

                # Iterar sobre los proyectos de ese cliente
                for _, project in client_projects.iterrows():
                    p_status = project['Planificación - Estado']
                    r_status = project['Recopilación de Datos - Estado']
                    g_status = project['Generación de informe - Estado']

                    # Usar Streamlit columns para simular la barra segmentada
                    col_pname, col_p, col_r, col_g = st.columns([4, 2, 2, 2])

                    with col_pname:
                        st.markdown(f"**{project['Nombre del Proyecto']}**")

                    with col_p:
                        # Barrita Planificación (P.)
                        color = COLOR_MAP.get(p_status, COLOR_MAP['No Iniciado'])
                        st.markdown(f"""
                            <div style='background-color: {color}; color: white; padding: 5px; border-radius: 4px; text-align: center;'>
                                P.
                            </div>
                        """, unsafe_allow_html=True)

                    with col_r:
                        # Barrita Recopilación (R.)
                        color = COLOR_MAP.get(r_status, COLOR_MAP['No Iniciado'])
                        # Usamos texto negro si el fondo es amarillo claro para mejor contraste
                        text_color = '#000000' if color == COLOR_MAP['En Proceso'] else '#FFFFFF'
                        st.markdown(f"""
                            <div style='background-color: {color}; color: {text_color}; padding: 5px; border-radius: 4px; text-align: center;'>
                                R.
                            </div>
                        """, unsafe_allow_html=True)

                    with col_g:
                        # Barrita Informe (I.)
                        color = COLOR_MAP.get(g_status, COLOR_MAP['No Iniciado'])
                        text_color = '#000000' if color == COLOR_MAP['En Proceso'] else '#FFFFFF'
                        st.markdown(f"""
                            <div style='background-color: {color}; color: {text_color}; padding: 5px; border-radius: 4px; text-align: center;'>
                                I.
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---", help="Separador de proyectos")