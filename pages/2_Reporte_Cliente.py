import streamlit as st
import gspread
import pandas as pd
import os
import re
import plotly.graph_objects as go
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

# ... (Mantén el diccionario EVALUATION_MAP completo e intacto aquí) ...
EVALUATION_MAP = {
    "Granos": {
        "worksheet": "Granos",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 5, "..."),
            ("Item 2: Línea de guiado.", 5, "..."),
            ("Item 3: Organización altamente conectada.", 10, "..."),
            ("Item 4: Uso de planificador de trabajo.", 15, "..."),
            ("Item 5: Uso de Operations Center Mobile.", 10, "..."),
            ("Item 6: JDLink.", 5, "..."),
            ("Item 7: Envío remoto. Mezcla de tanque.", 10, "..."),
            ("Item 8: % uso de autotrac en Tractor.", 10, "..."),
            ("Item 9: % uso autotrac Cosecha.", 10, "..."),
            ("Item 10: % uso autotrac Pulverización.", 10, "..."),
            ("Item 11: Uso de funcionalidades avanzadas.", 15, "..."),
            ("Item 12: Uso de tecnologías integradas.", 10, "..."),
            ("Item 13: Señal de corrección StarFire.", 5, "..."),
            ("Item 14: Paquete CSC.", 10, "..."),
            ("Item 15: Vinculación de API.", 5, "..."),
            ("Item 16: JDLink en otra marca.", 15, "..."),
        ]
    },
    "Ganadería": {
        "worksheet": "Ganadería",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15, "..."),
            ("Item 2: Digitalizar capa de siembra y mapa de picado.", 10, "..."),
            ("Item 3: Uso de planificador de trabajo.", 20, "..."),
            ("Item 4: Equipo registrados en el Centro de Operaciones.", 5, "..."),
            ("Item 5: Operadores registrados en el Centro de Operaciones.", 5, "..."),
            ("Item 6: Productos registrados en el Centro de Operaciones.", 5, "..."),
            ("Item 7: Uso de Operations Center Mobile.", 10, "..."),
            ("Item 8: JDLink activado en máquinas John Deere.", 10, "..."),
            ("Item 9: Planes de mantenimiento en tractores.", 10, "..."),
            ("Item 10: Mapeo de constituyentes.", 20, "..."),
            ("Item 11: Conectividad alimentación.", 20, "..."),
            ("Item 12: Generación de informes.", 10, "..."),
            ("Item 13: Paquete contratado con el concesionario (CSC).", 10, "..."),
        ]
    },
    "Cultivos de Alto Valor": {
        "worksheet": "Cultivos de Alto Valor",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15, "..."),
            ("Item 2: Lineas de guiado.", 5, "..."),
            ("Item 3: Tener al menos una labor digitalizada.", 10, "..."),
            ("Item 4: Uso de planificador de trabajo para alguna operación.", 15, "..."),
            ("Item 5: Uso del Operations Center Mobile.", 10, "..."),
            ("Item 6: JDLink activado en máquinas John Deere.", 10, "..."),
            ("Item 7: % uso de autotrac en Tractor.", 20, "..."),
            ("Item 8: Implement Guidance.", 20, "..."),
            ("Item 9: Señal de corrección StarFire.", 10, "..."),
            ("Item 10: Paquete contratado con el concesionario (CSC).", 10, "..."),
            ("Item 11: Equipos Registrados en Operations Center.", 5, "..."),
            ("Item 12: Operadores registrados en Operations Center.", 5, "..."),
            ("Item 13: Productos registrados en el Operations Center.", 5, "..."),
            ("Item 14: Configuración de Alertas Personalizables.", 10, "..."),
        ]
    }
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
    """Carga y devuelve todos los datos de una hoja específica en un DataFrame."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        _ = force_reload_key
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al cargar datos de {worksheet_name}: {e}")
        return pd.DataFrame()


def get_record_data(selected_id, selected_timestamp, category):
    """Carga los datos detallados de evaluación para el cliente y timestamp seleccionados."""
    try:
        worksheet_name = EVALUATION_MAP[category]["worksheet"]
        eval_df = load_worksheet_data(worksheet_name)

        record = eval_df[
            (eval_df['ID Cliente'].astype(str) == selected_id) &
            (eval_df['Fecha y Hora'].astype(str) == selected_timestamp)
            ]

        if record.empty:
            return None

        return record.iloc[0]
    except Exception as e:
        st.error(f"Error al obtener datos detallados de la hoja {category}: {e}")
        return None


# -----------------------------------------------------------
# INTERFAZ Y VISUALIZACIÓN
# -----------------------------------------------------------

# Inicializamos el estado de sesión para el cliente seleccionado
if 'report_client_select' not in st.session_state:
    st.session_state.report_client_select = 'Selecciona un registro'

# --- CONTROLES DE FILTRO DENTRO DE UN EXPANDER ---
with st.expander("-", expanded=True): # Renombrado el expander
    st.subheader("Selección de Cliente")
    st.markdown("Seleccione un registro de cliente para visualizar el análisis detallado.")

    # 1. BOTÓN DE RECARGA DE DATOS
    if st.button("🔄 Cargar Últimos Datos (Forzar Actualización de caché)"):
        load_worksheet_data.clear()
        st.session_state.data_reload_success = True
        st.rerun()

    if 'data_reload_success' in st.session_state and st.session_state.data_reload_success:
        st.success("¡Datos actualizados desde Google Sheets con éxito!")
        st.session_state.data_reload_success = False

    st.markdown("---")

    # 2. SELECTOR DE CLIENTE
    try:
        main_df = load_worksheet_data(MAIN_WORKSHEET_NAME)

        if main_df.empty:
            st.warning(
                "No se encontraron registros de clientes en la 'Hoja 1'. Por favor, cargue una evaluación primero.")
        else:
            main_df['Cliente ID'] = (main_df['ID Cliente'].astype(str) +
                                     ' - ' + main_df['Cliente'].astype(str) +
                                     ' (' + main_df['Fecha y Hora'].astype(str) + ')')

            client_options = ['Selecciona un registro'] + main_df['Cliente ID'].tolist()

            # Usamos el selectbox para actualizar el st.session_state directamente
            st.session_state.report_client_select = st.selectbox(
                "📝 Seleccionar Cliente y Fecha de Evaluación",
                options=client_options,
                key='selectbox_report_client_select',  # Nombre distinto al session_state para evitar conflictos
                index=client_options.index(
                    st.session_state.report_client_select) if st.session_state.report_client_select in client_options else 0
            )

    except Exception as e:
        st.error(f"Error al cargar la lista de clientes: {e}")
        st.stop()

    st.markdown("---")
# Fin del Expander

# Obtenemos la selección del estado de sesión
selected_client_id_combined = st.session_state.report_client_select

# --- PROCESAMIENTO Y VISUALIZACIÓN DEL REPORTE ---

if selected_client_id_combined != 'Selecciona un registro':

    try:
        # 1. Extracción de datos clave
        parts = selected_client_id_combined.split(' - ')
        id_cliente_report = parts[0]
        timestamp_match = re.search(r'\((.*?)\)$', selected_client_id_combined)
        timestamp_report = timestamp_match.group(1) if timestamp_match else None

        # Recargar main_df para asegurar que el registro existe, especialmente después de la recarga de caché
        main_df = load_worksheet_data(MAIN_WORKSHEET_NAME)
        record_main = main_df[
            (main_df['ID Cliente'].astype(str) == id_cliente_report) &
            (main_df['Fecha y Hora'].astype(str) == timestamp_report)
            ].iloc[0]

        category = record_main['Categoría de evaluación']
        total_score_obtained = pd.to_numeric(record_main['PUNTAJE TOTAL SMARTFARM'], errors='coerce',
                                             downcast='integer')

        record_eval = get_record_data(id_cliente_report, timestamp_report, category)

        if record_eval is None:
            st.error("No se pudo encontrar el registro de evaluación detallada. Verifique las hojas de categorías.")
            st.stop()

        # --- 2. VISTA GENERAL DE RESULTADOS (KEY METRICS) ---
        # ESTE TÍTULO COMIENZA LA PARTE NO OCULTABLE
        st.header(f"⭐ Resultado SmartFarm - {record_main['Cliente']} ({category})")

        category_map = EVALUATION_MAP[category]
        max_total_score = sum([max_score for _, max_score, _ in category_map["items"]])
        percentage = (total_score_obtained / max_total_score) * 100 if max_total_score > 0 else 0

        col_g2, col_g3, col_g4 = st.columns(3)

        with col_g2:
            st.metric(label="Puntaje Total Obtenido", value=f"{total_score_obtained}")
        with col_g3:
            st.metric(label="Puntaje Máximo Posible", value=f"{max_total_score}")
        with col_g4:
            st.metric(label="Porcentaje de Avance", value=f"{percentage:.1f} %")

        st.markdown("---")

        # --- 3. TABLA DETALLADA DE ÍTEMS Y PUNTAJES ---
        st.header("📋 Detalle de Puntuación por Ítem")

        item_data = []

        for item_name, max_score, _ in category_map["items"]:
            obtained_score = pd.to_numeric(record_eval.get(item_name, 0), errors='coerce', downcast='integer')

            item_data.append({
                "Ítem": item_name,
                "Puntaje Obtenido": obtained_score,
                "Puntaje Máximo": max_score,
                "Avance (%)": (obtained_score / max_score) * 100 if max_score > 0 else 0
            })

        detail_df = pd.DataFrame(item_data)

        styled_df = detail_df.style.format({
            "Avance (%)": "{:.1f}%",
            "Puntaje Obtenido": "{:.0f}",
            "Puntaje Máximo": "{:.0f}"
        }).background_gradient(cmap='YlGn', subset=['Avance (%)'])

        # CÁLCULO DE ALTURA DINÁMICA: 35 píxeles por fila + 30 píxeles para el encabezado
        df_height = (len(detail_df) * 35) + 30

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=df_height
        )

        st.markdown("---")

        # --- 4. GRÁFICO DE FORTALEZAS (RADAR CHART) ---
        st.header("📈 Gráfico de Fortalezas (Avance por Ítem)")

        r_values = detail_df['Avance (%)'].tolist()
        theta_values = detail_df['Ítem'].apply(lambda x: x.split(': ')[0]).tolist()

        if r_values:
            r_values.append(r_values[0])
            theta_values.append(theta_values[0])

        fig = go.Figure(
            data=[
                go.Scatterpolar(
                    r=r_values,
                    theta=theta_values,
                    fill='toself',
                    name='Avance (%)',
                    line_color='darkgreen',
                    opacity=0.8,
                    hovertemplate='<b>%{theta}</b>: %{r:.1f}%<extra></extra>'
                )
            ],
            layout=go.Layout(
                title=go.layout.Title(text=f"SmartFarm - {category}", x=0.5),
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        tickangle=0,
                        tickfont=dict(size=10),
                        angle=90,
                    ),
                    angularaxis=dict(
                        direction="clockwise",
                        period=len(theta_values) - 1,
                        tickfont=dict(size=12)
                    )
                ),
                showlegend=False,
                height=550  # <--- ALTURA REDUCIDA DE 800 a 550
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- 5. ESPACIO PARA RECOMENDACIONES ---
        st.header("✍️ Recomendaciones y Notas del Asesor")

        with st.form("recommendations_form"):
            st.text_area(
                "-",
                height=150,
                key="recommendation_text"
            )

            # Este botón actualmente no guarda la recomendación de forma permanente
            # Se requeriría lógica adicional (una columna en Hoja 1) para guardar este texto
            st.form_submit_button("Guardar Recomendaciones")

    except Exception as e:
        st.error(f"Error al cargar el reporte del cliente: {e}. Por favor, verifique la selección.")

else:
    st.info(
        "Por favor, seleccione un cliente en la sección de 'Controles de Filtro y Recarga' para generar el reporte de evaluación.")