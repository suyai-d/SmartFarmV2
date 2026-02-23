import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import io
import os
import tempfile  # Librería para manejo de archivos temporales
from fpdf import FPDF
from conexion import load_data, get_gspread_client, SHEET_ID, MAIN_WORKSHEET_NAME

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Reporte SmartFarm - Conci",
    layout="wide",
    page_icon="sf1.png"
)

# --- DICCIONARIO DE EVALUACIÓN CON CRITERIOS 25/26 ---
# (Se mantiene igual que el anterior, lo omito aquí para no hacer el bloque gigante,
# pero mantené el tuyo con todas las descripciones)
EVALUATION_MAP = {
    "Granos": {
        "worksheet": "Granos",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 5,
             "Campos con límites / Campos totales. Considerar: <60% pts=0. 60-70% 1pt | 70-80% 2pts | 80-90% 3pts | 90-95% 4pts | >95% 5pts."),
            ("Item 2: Línea de guiado.", 5,
             "Campos con guiado / Campos totales. Requisito: >40% para puntuar. 40-60% 1pt | 60-70% 2pts | 70-80% 3pts | 80-90% 4pts | >90% 5pts."),
            ("Item 3: Organización altamente conectada.", 10, "Al menos un campo con tres tipos de labores cargadas."),
            ("Item 4: Uso de planificador de trabajo.", 15,
             "Planes enviados entre 1-jun-25 y 1-jun-26. 3 etapas (siembra/pulv/cos) con 20% avance. 5 pts c/u."),
            ("Item 5: Uso de Operations Center Mobile.", 10,
             "Video navegación móvil: pantalla inicial, equipo, mapa campaña 25/26 y planificador."),
            ("Item 6: JDLink.", 5,
             "Máquinas con JDLink activo / Total. <30% pts=0. 40-50% 1pt | 50-60% 2pts | 60-70% 3pts | 70-80% 4pts | >80% 5pts."),
            ("Item 7: Envío remoto. Mezcla de tanque.", 5,
             "Mezcla generada anterior a Feb-2026 o uso de órdenes de trabajo en SIA."),
            ("Item 8: % uso de autotrac en Tractor.", 10,
             "Promedio 40% de uso en tractores >140 hp (1-jun-25 a 1-jun-26)."),
            ("Item 9: % uso autotrac Cosecha.", 10, "Promedio 70% de uso en cosechadoras (1-jun-25 a 1-jun-26)."),
            ("Item 10: % uso autotrac Pulverización.", 10,
             "Promedio 70% de uso en pulverizadoras (1-jun-25 a 1-jun-26)."),
            ("Item 11: Uso de funcionalidades avanzadas.", 15,
             "Autopath, ATTA, Guiado Pasivo o Machine Sync. Uso: 5 pts. >50% en un equipo: +10 pts."),
            ("Item 12: Uso de tecnologías integradas.", 15,
             "Cosecha: 5 pts | Pulverización: 5 pts | Uso >50% en algún equipo: +5 pts."),
            ("Item 13: Señal de corrección StarFire.", 10,
             "Uso de SF2, SF3, SF-RTK o RTK: 5 pts. Uso específico SF-RTK: +5 pts."),
            ("Item 14: Paquete CSC.", 5, "Factura del paquete contratado vigente."),
            ("Item 15: Vinculación de API.", 5, "Conexión mayor a 4 meses desde la fecha del informe."),
            ("Item 16: JDLink en otra marca.", 15, "Equipos de otras marcas visibles en OC (PLA no cuenta)."),
        ]
    },
    "Ganadería": {
        "worksheet": "Ganadería",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 10,
             "60-70% 2pts | 70-80% 4pts | 80-90% 6pts | 90-95% 8pts | >95% 10pts."),
            ("Item 2: Labor Digitalizada", 10, "Capa de siembra y cosecha. Siembra/Ferti variable: +5 pts."),
            ("Item 3: Uso de planificador de trabajo.", 15,
             "Planes 1-jun-25 a 1-jun-26. 5 pts por etapa (siembra, cosecha, aplicación)."),
            ("Item 4: Equipo registrados en el Centro de Operaciones.", 5,
             "Dos equipos y un implemento de alimentación (cargador frontal)."),
            ("Item 5: Operadores registrados en el Centro de Operaciones.", 5,
             "Al menos un empleado añadido en Gestor de Equipo."),
            ("Item 6: Productos registrados en el Centro de Operaciones.", 5,
             "Químicos, fertilizantes o variedades registradas."),
            ("Item 7: Uso de Operations Center Mobile.", 10,
             "Navegación campaña 25/26 y vista del planificador de trabajo."),
            ("Item 8: JDLink activado en máquinas John Deere.", 10,
             "40-50% 2pts | 50-60% 4pts | 60-70% 6pts | 70-80% 8pts | >80% 10pts."),
            ("Item 9: Planes de mantenimiento en tractores.", 10,
             "Planes personalizados cargados para máquinas John Deere."),
            ("Item 10: Mapeo de constituyentes.", 15,
             "Sensado de constituyentes temporada 25/26 visible en Analizador."),
            ("Item 11: Mapeo de Corte o Henificación", 15, "Mapa de corte o henificación temporada 25/26."),
            ("Item 12: Conectividad alimentación.", 20,
             "Tractor con conectividad visible y recorrido en patio de comida."),
            ("Item 13: Alertas Personalizables", 15, "Ralentí, velocidad o combustible. Fecha anterior a 31/01/2026."),
            ("Item 14: Paquete contratado con el concesionario (CSC).", 5, "Factura del paquete contratado."),
        ]
    },
    "Cultivos de Alto Valor": {
        "worksheet": "Cultivos de Alto Valor",
        "items": [
            ("Item 1: Organización y estandarización de lotes.", 15,
             "60-70% 3pts | 70-80% 6pts | 80-90% 9pts | 90-95% 12pts | >95% 15pts."),
            ("Item 2: Labor Digitalizada.", 10, "Informe en PDF del Analizador de Trabajo de cualquier operación."),
            ("Item 3: Uso del Operations Center Mobile.", 10, "Navegación campaña 25/26 y vista de planificador."),
            ("Item 4: JDLink activado en máquinas John Deere.", 10,
             "40-50% 2pts | 50-60% 4pts | 60-70% 6pts | 70-80% 8pts | >80% 10pts."),
            ("Item 5: Lineas de guiado", 5, "Mínimo 20% campos con guiado. >80% para 5 pts."),
            ("Item 6: % uso de Autotrac en Tractor", 20, "Promedio 30% uso en tractores <140 hp (25/26)."),
            ("Item 7: Uso de funcionalidades avanzadas: Guiado Pasivo de Implemento", 20,
             "Al menos un equipo utilizando Guiado Pasivo."),
            ("Item 8: Señal de corrección StarFire.", 10, "SF2, SF3, SF-RTK, RTK: 5 pts. Señal SF-RTK: +5 pts."),
            ("Item 9: Paquete contratado con el concesionario (CSC).", 5, "Factura del paquete contratado."),
            ("Item 10: Equipos Registrados en Operations Center.", 5, "2 equipos y 1 implemento registrados."),
            ("Item 11: Operadores registrados en Operations Center.", 5, "Al menos un empleado añadido."),
            ("Item 12: Productos registrados en el Operations Center.", 5, "Producto químico o variedad registrada."),
            ("Item 13: Alertas Personalizables.", 15, "Aviso activo (combustible/ralentí) anterior a 31/01/2026."),
            ("Item 14: Uso del planificador de trabajo para alguna operacion.", 15,
             "Al menos un trabajo en estado importado (jun-25 a jun-26)."),
        ]
    }
}


# --- FUNCIÓN PARA CREAR GRÁFICO DE RADAR ---
def crear_radar_chart(items_cfg, detalle):
    labels = [item[0].split(":")[0] for item in items_cfg]
    valores = []
    for item in items_cfg:
        val = pd.to_numeric(detalle.get(item[0].upper(), 0), errors='coerce')
        valores.append((val / item[1] * 100) if item[1] > 0 else 0)

    fig = go.Figure(data=go.Scatterpolar(
        r=valores + [valores[0]],
        theta=labels + [labels[0]],
        fill='toself',
        fillcolor='rgba(40, 167, 69, 0.3)',
        line=dict(color='#28a745', width=2)
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=40, r=40, t=20, b=20)
    )
    return fig


# --- FUNCIÓN GENERADORA DE PDF (CON ARCHIVO TEMPORAL) ---
def generar_pdf(nombre_cliente, categoria, score, score_max, tabla_data, recomendaciones, items_glosario, radar_fig):
    pdf = FPDF()
    pdf.add_page()

    # Logos
    try:
        pdf.image("logo_conci.png", x=10, y=8, w=40)
        pdf.image("logo_desafio.png", x=175, y=10, w=15)
    except:
        pass

    pdf.ln(25)
    pdf.set_font("Arial", 'B', 16);
    pdf.set_text_color(40, 167, 69)
    pdf.cell(190, 10, "Reporte de Certificacion SmartFarm", 0, 1, 'C');
    pdf.ln(5)

    # Datos Generales
    pdf.set_text_color(0, 0, 0);
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Cliente: {nombre_cliente}", 0, 0)
    pdf.cell(95, 8, f"Categoria: {categoria}", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Puntaje: {score:.0f} / {score_max:.0f}", 0, 0)
    perc = (score / score_max * 100) if score_max > 0 else 0
    pdf.cell(95, 8, f"Avance: {perc:.1f}%", 0, 1);
    pdf.ln(4)

    # Bloque Certificación
    pdf.set_font("Arial", 'B', 12)
    if score >= 105:
        pdf.set_fill_color(40, 167, 69);
        pdf.set_text_color(255, 255, 255)
        txt = "ESTADO: CLIENTE CERTIFICADO SMARTFARM"
    else:
        pdf.set_fill_color(230, 230, 230);
        pdf.set_text_color(100, 100, 100)
        txt = "ESTADO: EN PROCESO DE CERTIFICACION"
    pdf.cell(190, 10, txt, 0, 1, 'C', True)
    pdf.set_text_color(0, 0, 0);
    pdf.ln(5)

    # --- INSERTAR GRÁFICO DE RADAR (VERSION COMPACTA) ---
    try:
        # Generamos la imagen un poco más pequeña en resolución para que no pese tanto
        img_bytes = radar_fig.to_image(format="png", width=700, height=450)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(img_bytes)
            tmp_path = tmp.name

        # Reducimos 'w' (ancho) a 85 y ajustamos la posición x para centrarlo (x=60 aprox)
        # Bajamos un poco el y para que no pise el bloque de certificación
        pdf.image(tmp_path, x=58, y=pdf.get_y() + 2, w=85)

        # Reducimos el salto de línea que sigue al gráfico (antes era 75)
        pdf.ln(65)

        os.unlink(tmp_path)

    except Exception as e:
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(190, 10, f"(Gráfico no disponible: {e})", 0, 1, 'C')

    # Tabla
    pdf.set_font("Arial", 'B', 9);
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(130, 8, "Punto Evaluado", 1, 0, 'C', True)
    pdf.cell(30, 8, "Pts", 1, 0, 'C', True)
    pdf.cell(30, 8, "Estado", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 8)
    for row in tabla_data:
        pdf.cell(130, 7, row["Punto Evaluado"][:75], 1)
        pdf.cell(30, 7, row["Puntaje"], 1, 0, 'C')
        pdf.cell(30, 7, row["Estado"].replace("✅ ", "").replace("⚠️ ", "").replace("❌ ", ""), 1, 1, 'C')

    if recomendaciones:
        pdf.ln(5);
        pdf.set_font("Arial", 'B', 10);
        pdf.set_text_color(40, 167, 69)
        pdf.cell(190, 7, "Plan de Accion:", 0, 1)
        pdf.set_font("Arial", '', 9);
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(190, 5, recomendaciones)

    # NUEVA PÁGINA: GLOSARIO
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14);
    pdf.set_text_color(40, 167, 69)
    pdf.cell(190, 10, "Glosario de Criterios de Evaluacion 25/26", 0, 1, 'C');
    pdf.ln(5)

    pdf.set_text_color(0, 0, 0)
    for name, max_s, desc in items_glosario:
        pdf.set_font("Arial", 'B', 9);
        pdf.multi_cell(190, 5, f"{name} (Max: {max_s} pts)")
        pdf.set_font("Arial", '', 8);
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(185, 4, f"Criterio: {desc}")
        pdf.ln(2);
        pdf.line(10, pdf.get_y(), 200, pdf.get_y());
        pdf.ln(2)
        pdf.set_text_color(0, 0, 0)

    return pdf.output(dest='S').encode('latin-1', 'ignore')


# --- UI STREAMLIT Y CARGA ---
# (Mantené el resto de tu lógica de UI de búsqueda y carga que ya funcionaba)

def get_record_detailed(selected_id, selected_timestamp, category):
    try:
        df_cat = load_data(EVALUATION_MAP[category]["worksheet"])
        record = df_cat[(df_cat['ID CLIENTE'].astype(str) == str(selected_id)) &
                        (df_cat['FECHA Y HORA'].astype(str) == str(selected_timestamp))]
        return record.iloc[0] if not record.empty else None
    except:
        return None


st.title("📋 Generador de Reportes SmartFarm")
main_df = load_data(MAIN_WORKSHEET_NAME)

if not main_df.empty:
    main_df['Selector'] = main_df['ID CLIENTE'].astype(str) + " - " + main_df['CLIENTE'].astype(str) + " (" + main_df[
        'FECHA Y HORA'].astype(str) + ")"
    seleccion = st.selectbox("🔍 Seleccionar Cliente:", ["..."] + main_df['Selector'].tolist())

    if seleccion != "...":
        id_sel = seleccion.split(" - ")[0]
        ts_sel = re.search(r'\((.*?)\)', seleccion).group(1)
        datos_p = \
        main_df[(main_df['ID CLIENTE'].astype(str) == id_sel) & (main_df['FECHA Y HORA'].astype(str) == ts_sel)].iloc[0]

        cat_sel = datos_p['CATEGORÍA DE EVALUACIÓN']
        detalle = get_record_detailed(id_sel, ts_sel, cat_sel)

        if detalle is not None:
            items_cfg = EVALUATION_MAP[cat_sel]["items"]
            score_obt = pd.to_numeric(datos_p['PUNTAJE TOTAL SMARTFARM'], errors='coerce')
            score_max = sum(i[1] for i in items_cfg)

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Puntaje", f"{score_obt:.0f}")
            c2.metric("Meta", "105 pts")
            c3.metric("Avance", f"{(score_obt / score_max * 100):.1f}%")

            fig_radar = crear_radar_chart(items_cfg, detalle)
            st.plotly_chart(fig_radar, use_container_width=True)

            tabla_data = []
            for item in items_cfg:
                v = pd.to_numeric(detalle.get(item[0].upper(), 0), errors='coerce')
                est = "✅ Óptimo" if v == item[1] else "⚠️ Mejorable" if v > 0 else "❌ Pendiente"
                tabla_data.append({"Punto Evaluado": item[0], "Puntaje": f"{v:.0f}/{item[1]}", "Estado": est})

            st.table(pd.DataFrame(tabla_data))
            txt_reco = st.text_area("Comentarios y Plan de Acción:", height=150)

            if st.download_button(
                    "📥 Descargar PDF con Gráfico y Glosario",
                    data=generar_pdf(datos_p['CLIENTE'], cat_sel, score_obt, score_max, tabla_data, txt_reco, items_cfg,
                                     fig_radar),
                    file_name=f"Reporte_{datos_p['CLIENTE']}.pdf",
                    mime="application/pdf", use_container_width=True
            ):
                st.balloons()
else:
    st.info("No hay datos disponibles.")
