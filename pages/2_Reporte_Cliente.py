import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from fpdf import FPDF
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Reporte SmartFarm - Conci",
    layout="wide",
    page_icon="sf1.png"
)

# --- DICCIONARIO DE EVALUACIÓN COMPLETO ---
EVALUATION_MAP = {
    "Granos": {
        "worksheet": "Granos",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 5),
            ("Item 2: Línea de guiado.", 5),
            ("Item 3: Organización altamente conectada.", 10),
            ("Item 4: Uso de planificador de trabajo.", 15),
            ("Item 5: Uso de Operations Center Mobile.", 10),
            ("Item 6: JDLink.", 5),
            ("Item 7: Envío remoto. Mezcla de tanque.", 10),
            ("Item 8: % uso de autotrac en Tractor.", 10),
            ("Item 9: % uso autotrac Cosecha.", 10),
            ("Item 10: % uso autotrac Pulverización.", 10),
            ("Item 11: Uso de funcionalidades avanzadas.", 15),
            ("Item 12: Uso de tecnologías integradas.", 10),
            ("Item 13: Señal de corrección StarFire.", 5),
            ("Item 14: Paquete CSC.", 10),
            ("Item 15: Vinculación de API.", 5),
            ("Item 16: JDLink en otra marca.", 15),
        ]
    },
    "Ganadería": {
        "worksheet": "Ganadería",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15),
            ("Item 2: Digitalizar capa de siembra y mapa de picado.", 10),
            ("Item 3: Uso de planificador de trabajo.", 20),
            ("Item 4: Equipo registrados en el Centro de Operaciones.", 5),
            ("Item 5: Operadores registrados en el Centro de Operaciones.", 5),
            ("Item 6: Productos registrados en el Centro de Operaciones.", 5),
            ("Item 7: Uso de Operations Center Mobile.", 10),
            ("Item 8: JDLink activado en máquinas John Deere.", 10),
            ("Item 9: Planes de mantenimiento en tractores.", 10),
            ("Item 10: Mapeo de con-stituyentes.", 20),
            ("Item 11: Conectividad alimentación.", 20),
            ("Item 12: Generación de informes.", 10),
            ("Item 13: Paquete contratado con el concesionario (CSC).", 10),
        ]
    },
    "Cultivos de Alto Valor": {
        "worksheet": "Cultivos de Alto Valor",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15),
            ("Item 2: Lineas de guiado.", 5),
            ("Item 3: Tener al menos una labor digitalizada.", 10),
            ("Item 4: Uso de planificador de trabajo para alguna operación.", 15),
            ("Item 5: Uso del Operations Center Mobile.", 10),
            ("Item 6: JDLink activado en máquinas John Deere.", 10),
            ("Item 7: % uso de autotrac en Tractor.", 20),
            ("Item 8: Implement Guidance.", 20),
            ("Item 9: Señal de corrección StarFire.", 10),
            ("Item 10: Paquete contratado con el concesionario (CSC).", 10),
            ("Item 11: Equipos Registrados en Operations Center.", 5),
            ("Item 12: Operadores registrados en Operations Center.", 5),
            ("Item 13: Productos registrados en el Operations Center.", 5),
            ("Item 14: Configuración de Alertas Personalizables.", 10),
        ]
    }
}


# --- FUNCIÓN GENERADORA DE PDF ---
def generar_pdf(nombre_cliente, categoria, score, score_max, tabla_data, recomendaciones):
    pdf = FPDF()
    pdf.add_page()

    # Encabezado con Logos
    try:
        pdf.image("logo_conci.png", x=10, y=8, w=40)
        pdf.image("logo_desafio.png", x=175, y=10, w=15)
    except:
        pass

    pdf.ln(25)  # Espacio tras los logos

    # Título Principal
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(40, 167, 69)
    pdf.cell(190, 10, "Reporte de Adopcion Tecnologica SmartFarm", 0, 1, 'C')
    pdf.ln(5)

    # Datos Generales
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(95, 10, f"Cliente: {nombre_cliente}", 0, 0)
    pdf.cell(95, 10, f"Categoria: {categoria}", 0, 1)

    pdf.set_font("Arial", '', 12)
    pdf.cell(95, 10, f"Puntaje Obtenido: {score:.0f} / {score_max:.0f}", 0, 0)
    perc = (score / score_max * 100) if score_max > 0 else 0
    pdf.cell(95, 10, f"Nivel de Adopcion: {perc:.1f}%", 0, 1)
    pdf.ln(10)

    # Tabla de Resultados
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(130, 10, "Punto Evaluado", 1, 0, 'C', True)
    pdf.cell(30, 10, "Puntaje", 1, 0, 'C', True)
    pdf.cell(30, 10, "Estado", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 9)
    for row in tabla_data:
        y_before = pdf.get_y()
        pdf.multi_cell(130, 8, row["Punto Evaluado"], 1)
        y_after = pdf.get_y()
        h = y_after - y_before

        pdf.set_xy(140, y_before)
        pdf.cell(30, h, row["Puntaje"], 1, 0, 'C')
        txt_estado = row["Estado"].replace("✅ ", "").replace("⚠️ ", "").replace("❌ ", "")
        pdf.cell(30, h, txt_estado, 1, 1, 'C')

    # Recomendaciones Finales
    if recomendaciones:
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(40, 167, 69)
        pdf.cell(190, 10, "Plan de Accion y Recomendaciones:", 0, 1, 'L')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(190, 7, recomendaciones, 0, 'L')

    return pdf.output(dest='S').encode('latin-1', 'ignore')


# --- FUNCIONES DE CARGA ---
def get_record_detailed(selected_id, selected_timestamp, category):
    try:
        ws_name = EVALUATION_MAP[category]["worksheet"]
        df_cat = load_data(ws_name)
        if df_cat.empty: return None
        record = df_cat[(df_cat['ID CLIENTE'].astype(str) == str(selected_id)) & (
                    df_cat['FECHA Y HORA'].astype(str) == str(selected_timestamp))]
        return record.iloc[0] if not record.empty else None
    except:
        return None


# --- INTERFAZ STREAMLIT ---
# 1. Encabezado visual con logos
col_logo1, col_vacia, col_logo2 = st.columns([1, 2, 1])
with col_logo1:
    st.image("logo_conci.png", width=200)
with col_logo2:
    st.image("logo_desafio.png", width=100)

st.title("📋 Reporte Individual de Cliente")

main_df = load_data(MAIN_WORKSHEET_NAME)

if not main_df.empty:
    main_df['Selector'] = main_df['ID CLIENTE'].astype(str) + " - " + main_df['CLIENTE'].astype(str) + " (" + main_df[
        'FECHA Y HORA'].astype(str) + ")"
    opciones = ["Seleccione un registro..."] + main_df['Selector'].tolist()
    seleccion = st.selectbox("🔍 Buscar Evaluación Guardada:", opciones)
else:
    st.warning("No hay datos cargados.")
    st.stop()

if seleccion != "Seleccione un registro...":
    try:
        id_sel = seleccion.split(" - ")[0]
        ts_sel = re.search(r'\((.*?)\)', seleccion).group(1)

        datos_p = \
        main_df[(main_df['ID CLIENTE'].astype(str) == id_sel) & (main_df['FECHA Y HORA'].astype(str) == ts_sel)].iloc[0]
        cat_sel = datos_p['CATEGORÍA DE EVALUACIÓN']
        detalle = get_record_detailed(id_sel, ts_sel, cat_sel)

        if detalle is not None:
            items_cfg = EVALUATION_MAP[cat_sel]["items"]
            score_obt = pd.to_numeric(datos_p['PUNTAJE TOTAL SMARTFARM'], errors='coerce')
            score_max = sum(item[1] for item in items_cfg)

            # KPIs
            st.divider()
            k1, k2, k3 = st.columns(3)
            k1.metric("Puntaje Obtenido", f"{score_obt:.0f} pts")
            k2.metric("Potencial Máximo", f"{score_max:.0f} pts")
            k3.metric("Nivel de Adopción", f"{(score_obt / score_max * 100):.1f}%")

            # Radar Chart
            st.subheader("📊 Gráfico de Fortalezas")
            labels = [item[0].split(":")[0] for item in items_cfg]
            valores = []
            for item in items_cfg:
                val = pd.to_numeric(detalle.get(item[0].upper(), 0), errors='coerce')
                valores.append((val / item[1] * 100) if item[1] > 0 else 0)

            fig = go.Figure(data=go.Scatterpolar(r=valores + [valores[0]], theta=labels + [labels[0]], fill='toself',
                                                 line_color='#28a745'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # Tabla de Recomendaciones
            st.subheader("📝 Detalle de Evaluación")
            tabla_data = []
            for item in items_cfg:
                v = pd.to_numeric(detalle.get(item[0].upper(), 0), errors='coerce')
                est = "✅ Óptimo" if v == item[1] else "⚠️ Mejorable" if v > 0 else "❌ Pendiente"
                tabla_data.append({"Punto Evaluado": item[0], "Puntaje": f"{v:.0f}/{item[1]}", "Estado": est})

            st.table(pd.DataFrame(tabla_data))

            # Sección de Plan de Acción
            st.subheader("💡 Plan de Acción Personalizado")
            txt_reco = st.text_area("Escriba sugerencias específicas para el cliente:",
                                    placeholder="Ej: Recomendamos instalar JDLink en el tractor principal para mejorar la conectividad...",
                                    height=150)

            # Botón de Descarga
            st.divider()
            pdf_bytes = generar_pdf(datos_p['CLIENTE'], cat_sel, score_obt, score_max, tabla_data, txt_reco)

            st.download_button(
                label="📥 Descargar Reporte Completo en PDF",
                data=pdf_bytes,
                file_name=f"Reporte_SmartFarm_{datos_p['CLIENTE']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error al procesar el reporte: {e}")
