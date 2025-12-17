import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# 1. Configuración de página
st.set_page_config(
    page_title="Reporte SmartFarm - Conci",
    layout="wide",
    page_icon="sf1.png"
)

# --- DICCIONARIO DE EVALUACIÓN (Mantenlo completo) ---
# He simplificado el snippet aquí, pero usa tu diccionario EVALUATION_MAP completo
EVALUATION_MAP = {
    "Granos": {"worksheet": "Granos", "items": [
        ("Item 1: Organización y estandarización de lotes.", 5, "..."),
        ("Item 2: Línea de guiado.", 5, "..."),
        # ... (restantes ítems)
    ]},
    "Ganadería": {"worksheet": "Ganadería", "items": [
        ("Item 1: Organización y estandarización de lotes.", 15, "..."),
        # ... (restantes ítems)
    ]},
    "Cultivos de Alto Valor": {"worksheet": "Cultivos de Alto Valor", "items": [
        ("Item 1: Organización y estandarización de lotes.", 15, "..."),
        # ... (restantes ítems)
    ]}
}


# --- FUNCIONES DE APOYO ---

def get_record_detailed(selected_id, selected_timestamp, category):
    """Busca el registro específico en la hoja de la categoría correspondiente"""
    try:
        ws_name = EVALUATION_MAP[category]["worksheet"]
        df_cat = load_data(ws_name)

        # Filtro estricto por ID y Fecha/Hora
        record = df_cat[
            (df_cat['ID Cliente'].astype(str) == str(selected_id)) &
            (df_cat['Fecha y Hora'].astype(str) == str(selected_timestamp))
            ]
        return record.iloc[0] if not record.empty else None
    except Exception as e:
        st.error(f"Error recuperando detalle: {e}")
        return None


# --- INTERFAZ DE USUARIO ---

st.title("📋 Reporte Individual de Cliente")

# Selector de cliente en la barra lateral o expander
with st.expander("🔍 Filtros de Búsqueda", expanded=True):
    main_df = load_data(MAIN_WORKSHEET_NAME)

    if not main_df.empty:
        # Crear una etiqueta legible para el selector
        main_df['Selector'] = main_df['ID Cliente'].astype(str) + " - " + main_df['Cliente'] + " (" + main_df[
            'Fecha y Hora'].astype(str) + ")"
        opciones = ["Seleccione un registro..."] + main_df['Selector'].tolist()

        seleccion = st.selectbox("Buscar Evaluación:", opciones)
    else:
        st.warning("No hay datos disponibles en la Hoja Principal.")
        st.stop()

if seleccion != "Seleccione un registro...":
    # Extraer ID y Timestamp usando Regex o Split
    try:
        # Formato esperado: "ID - Nombre (Timestamp)"
        id_sel = seleccion.split(" - ")[0]
        ts_sel = re.search(r'\((.*?)\)', seleccion).group(1)

        # Obtener datos de Hoja Principal
        datos_principales = main_df[
            (main_df['ID Cliente'].astype(str) == id_sel) &
            (main_df['Fecha y Hora'].astype(str) == ts_sel)
            ].iloc[0]

        cat_sel = datos_principales['Categoría de evaluación']

        # Obtener datos de Hoja de Detalle
        detalle = get_record_detailed(id_sel, ts_sel, cat_sel)

        if detalle is not None:
            # --- KPIs SUPERIORES ---
            score_obtenido = pd.to_numeric(datos_principales['PUNTAJE TOTAL SMARTFARM'], errors='coerce')

            # Cálculo de puntaje máximo dinámico según el mapa
            items_config = EVALUATION_MAP[cat_sel]["items"]
            score_maximo = sum(item[1] for item in items_config)
            porcentaje = (score_obtenido / score_maximo * 100) if score_maximo > 0 else 0

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Puntaje Obtenido", f"{score_obtenido:.0f} pts")
            c2.metric("Potencial Máximo", f"{score_maximo:.0f} pts")
            c3.metric("Nivel de Adopción", f"{porcentaje:.1f}%")

            # --- GRÁFICO RADAR (ARAÑA) ---
            st.subheader("📊 Análisis de Fortalezas y Oportunidades")

            labels = [item[0].split(":")[0] for item in items_config]  # "Item 1", "Item 2"...
            valores = []
            for item in items_config:
                val = pd.to_numeric(detalle.get(item[0], 0), errors='coerce')
                # Convertir a porcentaje del ítem para que el radar sea equilibrado
                perc_item = (val / item[1] * 100) if item[1] > 0 else 0
                valores.append(perc_item)

            # Cerrar el círculo del radar
            labels.append(labels[0])
            valores.append(valores[0])

            fig = go.Figure(data=go.Scatterpolar(
                r=valores,
                theta=labels,
                fill='toself',
                line_color='#28a745',
                marker=dict(size=8)
            ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- TABLA DE RECOMENDACIONES ---
            st.subheader("📝 Recomendaciones por Punto")

            # Generar tabla comparativa
            tabla_data = []
            for item in items_config:
                val_obt = pd.to_numeric(detalle.get(item[0], 0), errors='coerce')
                tabla_data.append({
                    "Punto Evaluado": item[0],
                    "Puntaje": f"{val_obt}/{item[1]}",
                    "Estado": "✅ Óptimo" if val_obt == item[1] else "⚠️ Mejorable" if val_obt > 0 else "❌ Pendiente"
                })

            st.table(pd.DataFrame(tabla_data))

    except Exception as e:
        st.error(f"Error procesando el reporte: {e}")
else:
    st.info("💡 Selecciona un cliente arriba para generar el análisis visual.")
